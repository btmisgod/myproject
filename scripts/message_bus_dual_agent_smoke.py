import asyncio
import json
from dataclasses import dataclass
from typing import Any

import httpx
from app.core.exceptions import AppError

from app.services.delivery_adapter import WebhookDeliveryAdapter
from app.services.event_dispatcher import EventDispatcher
from app.services.message_bus import CommunityMessageBus
from app.services.message_envelope import MessageEnvelope, MessageTarget, envelope_timestamp_now
from app.services.protocol_validation_hook import ProtocolValidationHook


COMMUNITY_API_BASE_URL = "http://127.0.0.1:8000/api/v1"
GROUP_ID = "54b12c32-dbd3-46d8-97ee-22bf8a499709"


@dataclass(frozen=True)
class AgentEndpoint:
    name: str
    agent_id: str
    webhook_url: str
    webhook_secret: str
    token: str


NEKO = AgentEndpoint(
    name="neko",
    agent_id="345263e6-1d1a-4697-8dd5-b8b23f86392d",
    webhook_url="http://host.docker.internal:8787/community-webhook",
    webhook_secret="neko-webhook-secret-2026-v2",
    token="9Lmm-VuSl6rPnTCtDBUWEAesryq1SmXUNZ5mRKKzF-U",
)


AGENT_33 = AgentEndpoint(
    name="33",
    agent_id="648542c7-3eca-4028-8dc7-856c9ec90b3e",
    webhook_url="http://host.docker.internal:8788/community-webhook",
    webhook_secret="d8fcc2bc54262dfcd9f3a7dd4bbacab87f48b96fe57225c1",
    token="p-5qIxeEq8gHpD6UHXaRnDccdrv-AeTCWJnVfryN5Cw",
)


def make_bus(target: AgentEndpoint) -> CommunityMessageBus:
    return CommunityMessageBus(
        hooks=[ProtocolValidationHook()],
        dispatcher=EventDispatcher(
            adapters=[
                WebhookDeliveryAdapter(
                    default_webhook_url=target.webhook_url,
                    default_webhook_secret=target.webhook_secret,
                    timeout_seconds=45.0,
                )
            ]
        ),
    )


async def create_real_message(*, actor: AgentEndpoint, text: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{COMMUNITY_API_BASE_URL}/messages",
            headers={"X-Agent-Token": actor.token},
            json={
                "group_id": GROUP_ID,
                "message_type": "analysis",
                "content": {
                    "text": text,
                    "source": "message_bus_dual_agent_smoke.py",
                },
            },
        )
    response.raise_for_status()
    return response.json()["data"]


async def list_thread_messages(*, actor: AgentEndpoint, thread_id: str) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{COMMUNITY_API_BASE_URL}/messages",
            headers={"X-Agent-Token": actor.token},
            params={
                "group_id": GROUP_ID,
                "thread_id": thread_id,
                "limit": 50,
                "offset": 0,
            },
        )
    response.raise_for_status()
    return response.json()["data"]["items"]


async def wait_for_agent_reply(
    *,
    observer: AgentEndpoint,
    thread_id: str,
    expected_agent_id: str,
    parent_message_id: str,
    timeout_seconds: float = 45.0,
) -> dict[str, Any]:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while asyncio.get_running_loop().time() < deadline:
        items = await list_thread_messages(actor=observer, thread_id=thread_id)
        for item in items:
            if item["agent_id"] == expected_agent_id and item.get("parent_message_id") == parent_message_id:
                return item
        await asyncio.sleep(1.0)
    raise TimeoutError(f"timed out waiting for agent {expected_agent_id} reply in thread {thread_id}")


async def deliver_real_message_to_agent(
    *,
    source_message: dict[str, Any],
    target: AgentEndpoint,
    override_text: str | None = None,
) -> dict[str, Any]:
    bus = make_bus(target)
    payload = dict(source_message.get("content") or {})
    if override_text is not None:
        payload["text"] = override_text
    payload["message_type"] = source_message.get("message_type", "analysis")

    report = await bus.publish(
        MessageEnvelope(
            message_id=source_message["id"],
            category="channel_message",
            event_type="message.posted",
            channel_id=source_message["group_id"],
            source_agent=source_message["agent_id"],
            target=MessageTarget(target_scope="agent", target_agent_id=target.agent_id),
            thread_id=source_message["thread_id"],
            payload=payload,
            priority="normal",
            timestamp=envelope_timestamp_now(),
            metadata={"dual_agent_smoke": True, "target_agent": target.name},
        )
    )
    return {
        "route_type": report.routing_plan.route_type,
        "protocol_validation": report.envelope.metadata.get("protocol_validation"),
        "delivery_results": [item.metadata for item in report.delivery_results],
    }


async def run_pass_chain() -> None:
    seed_message = await create_real_message(
        actor=AGENT_33,
        text="dual-agent bootstrap parent",
    )

    to_neko = await deliver_real_message_to_agent(
        source_message=seed_message,
        target=NEKO,
        override_text="neko 请只回复两个字：收到",
    )

    neko_reply = await wait_for_agent_reply(
        observer=AGENT_33,
        thread_id=seed_message["thread_id"],
        expected_agent_id=NEKO.agent_id,
        parent_message_id=seed_message["id"],
    )

    to_33 = await deliver_real_message_to_agent(
        source_message=neko_reply,
        target=AGENT_33,
    )

    print(
        json.dumps(
            {
                "scenario": "dual_agent_pass",
                "seed_message_id": seed_message["id"],
                "seed_thread_id": seed_message["thread_id"],
                "neko_reply_id": neko_reply["id"],
                "neko_reply_text": neko_reply.get("content", {}).get("text"),
                "deliveries": {
                    "community_to_neko": to_neko,
                    "community_to_33": to_33,
                },
            },
            ensure_ascii=False,
        )
    )


async def run_warn_chain() -> None:
    seed_message = await create_real_message(
        actor=AGENT_33,
        text="dual-agent warn bootstrap parent",
    )

    bus = make_bus(NEKO)
    report = await bus.publish(
        MessageEnvelope(
            message_id=seed_message["id"],
            category="channel_message",
            event_type="message.posted",
            channel_id=seed_message["group_id"],
            source_agent=seed_message["agent_id"],
            target=None,
            thread_id=seed_message["thread_id"],
            payload={
                "text": "dual-agent warn payload",
                "message_type": "analysis",
            },
            priority="normal",
            timestamp=envelope_timestamp_now(),
            metadata={"dual_agent_smoke": True, "scenario": "warn", "target_agent": NEKO.name},
        )
    )
    print(
        json.dumps(
            {
                "scenario": "dual_agent_warn",
                "seed_message_id": seed_message["id"],
                "seed_thread_id": seed_message["thread_id"],
                "route_type": report.routing_plan.route_type,
                "protocol_validation": report.envelope.metadata.get("protocol_validation"),
                "delivery_results": [item.metadata for item in report.delivery_results],
            },
            ensure_ascii=False,
        )
    )


async def run_block_chain() -> None:
    bus = make_bus(NEKO)
    try:
        report = await bus.publish_message(
            group_id="",
            message_type="message.posted",
            payload={
                "text": "dual-agent block payload",
                "message_type": "analysis",
            },
            actor_agent_id=AGENT_33.agent_id,
            target_agent_id=NEKO.agent_id,
            thread_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            metadata={"dual_agent_smoke": True, "scenario": "block", "target_agent": NEKO.name},
        )
        print(
            json.dumps(
                {
                    "scenario": "dual_agent_block",
                    "ok": True,
                    "route_type": report.routing_plan.route_type,
                    "protocol_validation": report.envelope.metadata.get("protocol_validation"),
                    "delivery_results": [item.metadata for item in report.delivery_results],
                },
                ensure_ascii=False,
            )
        )
    except AppError as exc:
        print(
            json.dumps(
                {
                    "scenario": "dual_agent_block",
                    "ok": False,
                    "error_code": exc.code,
                    "message": str(exc),
                },
                ensure_ascii=False,
            )
        )


async def main() -> None:
    await run_pass_chain()
    await run_warn_chain()
    await run_block_chain()


if __name__ == "__main__":
    asyncio.run(main())
