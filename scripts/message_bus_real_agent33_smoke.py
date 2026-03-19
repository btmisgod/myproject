import asyncio
import json
import os
from pathlib import Path

import httpx
from app.core.exceptions import AppError
from app.services.delivery_adapter import WebhookDeliveryAdapter
from app.services.event_dispatcher import EventDispatcher
from app.services.message_bus import CommunityMessageBus
from app.services.message_envelope import MessageEnvelope, MessageTarget, envelope_timestamp_now
from app.services.protocol_validation_hook import ProtocolValidationHook


COMMUNITY_API_BASE_URL = "http://127.0.0.1:8000/api/v1"
AGENT_33_WEBHOOK_URL = "http://host.docker.internal:8788/community-webhook"
AGENT_33_WEBHOOK_SECRET = "d8fcc2bc54262dfcd9f3a7dd4bbacab87f48b96fe57225c1"
GROUP_ID = "54b12c32-dbd3-46d8-97ee-22bf8a499709"
SEED_AGENT_STATE_PATH = Path("/root/.openclaw/workspace/.openclaw/community-webhook-state.json")
SEED_AGENT_TOKEN = "9Lmm-VuSl6rPnTCtDBUWEAesryq1SmXUNZ5mRKKzF-U"


def load_seed_agent_state() -> dict:
    # Reuse an existing non-33 community agent state so the bootstrap message
    # is created via the real community API without introducing new setup flow.
    explicit_token = str(os.getenv("COMMUNITY_SEED_AGENT_TOKEN") or "").strip()
    if explicit_token:
        return {"token": explicit_token}
    if not SEED_AGENT_STATE_PATH.exists():
        return {"token": SEED_AGENT_TOKEN}
    return json.loads(SEED_AGENT_STATE_PATH.read_text(encoding="utf-8"))


def make_bus() -> CommunityMessageBus:
    return CommunityMessageBus(
        hooks=[ProtocolValidationHook()],
        dispatcher=EventDispatcher(
            adapters=[
                WebhookDeliveryAdapter(
                    default_webhook_url=AGENT_33_WEBHOOK_URL,
                    default_webhook_secret=AGENT_33_WEBHOOK_SECRET,
                    timeout_seconds=30.0,
                )
            ]
        ),
    )


async def create_real_parent_message() -> dict:
    seed = load_seed_agent_state()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{COMMUNITY_API_BASE_URL}/messages",
            headers={"X-Agent-Token": seed["token"]},
            json={
                "group_id": GROUP_ID,
                "message_type": "analysis",
                "content": {
                    # Keep this bootstrap message neutral so it does not
                    # accidentally trigger 33 through the existing event path.
                    "text": "bootstrap parent for real webhook smoke",
                    "source": "message_bus_real_agent33_smoke.py",
                },
            },
        )
    response.raise_for_status()
    payload = response.json()
    message = payload["data"]
    return {
        "message_id": message["id"],
        "thread_id": message["thread_id"],
        "agent_id": message["agent_id"],
    }


async def send_real_message_case(
    *,
    name: str,
    text: str,
    target_agent_id: str | None,
    extra_payload: dict | None = None,
) -> None:
    bus = make_bus()
    parent = await create_real_parent_message()
    try:
        payload = {
            "text": text,
            "message_type": "analysis",
        }
        if extra_payload:
            payload.update(extra_payload)
        report = await bus.publish(
            MessageEnvelope(
                message_id=parent["message_id"],
                category="channel_message",
                event_type="message.posted",
                channel_id=GROUP_ID,
                source_agent=parent["agent_id"],
                target=MessageTarget(target_scope="agent", target_agent_id=target_agent_id) if target_agent_id else None,
                thread_id=parent["thread_id"],
                payload=payload,
                priority="normal",
                timestamp=envelope_timestamp_now(),
                metadata={"smoke_parent_message_id": parent["message_id"], "smoke_case": name},
            )
        )
        print(
            json.dumps(
                {
                    "case": name,
                    "ok": True,
                    "parent_message_id": parent["message_id"],
                    "parent_thread_id": parent["thread_id"],
                    "route_type": report.routing_plan.route_type,
                    "protocol_validation": report.envelope.metadata.get("protocol_validation"),
                    "delivery_results": [item.metadata for item in report.delivery_results],
                },
                ensure_ascii=False,
            )
        )
    except AppError as exc:
        print(json.dumps({"case": name, "ok": False, "error_code": exc.code, "message": str(exc)}, ensure_ascii=False))


async def send_block_case() -> None:
    bus = make_bus()
    try:
        report = await bus.publish_message(
            group_id="",
            message_type="message.posted",
            payload={"text": "33 不应收到这条 block 测试消息。", "message_type": "analysis"},
            actor_agent_id="community-tester",
            target_agent_id="648542c7-3eca-4028-8dc7-856c9ec90b3e",
            thread_id="44444444-4444-4444-4444-444444444444",
        )
        print(
            json.dumps(
                {
                    "case": "block",
                    "ok": True,
                    "route_type": report.routing_plan.route_type,
                    "protocol_validation": report.envelope.metadata.get("protocol_validation"),
                    "delivery_results": [item.metadata for item in report.delivery_results],
                },
                ensure_ascii=False,
            )
        )
    except AppError as exc:
        print(json.dumps({"case": "block", "ok": False, "error_code": exc.code, "message": str(exc)}, ensure_ascii=False))


async def main() -> None:
    await send_real_message_case(
        name="pass",
        text="33 请确认收到这条 pass 测试消息。",
        target_agent_id="648542c7-3eca-4028-8dc7-856c9ec90b3e",
    )
    await send_real_message_case(
        name="warn",
        text="community smoke warn payload",
        target_agent_id=None,
    )
    await send_real_message_case(
        name="reroute_suggest",
        text="community smoke reroute payload wrong-channel",
        target_agent_id="648542c7-3eca-4028-8dc7-856c9ec90b3e",
        extra_payload={"marker": "wrong-channel"},
    )
    await send_block_case()


if __name__ == "__main__":
    asyncio.run(main())
