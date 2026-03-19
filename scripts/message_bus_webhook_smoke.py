import asyncio
import json
from pathlib import Path

from app.core.exceptions import AppError
from app.services.delivery_adapter import InternalConsumerAdapter, WebhookDeliveryAdapter
from app.services.event_dispatcher import EventDispatcher
from app.services.message_bus import CommunityMessageBus
from app.services.protocol_validation_hook import ProtocolValidationHook


RECEIVER_URL = "http://127.0.0.1:8799/webhook"
LOG_PATH = Path("/tmp/agent-community-webhook-smoke.jsonl")


def make_bus() -> CommunityMessageBus:
    return CommunityMessageBus(
        hooks=[ProtocolValidationHook()],
        dispatcher=EventDispatcher(
            adapters=[
                WebhookDeliveryAdapter(default_webhook_url=RECEIVER_URL),
                InternalConsumerAdapter(),
            ]
        ),
    )


async def send_case(name: str, **kwargs) -> None:
    bus = make_bus()
    try:
        report = await bus.publish_message(**kwargs)
        print(
            json.dumps(
                {
                    "case": name,
                    "ok": True,
                    "route_type": report.routing_plan.route_type,
                    "protocol_validation": report.envelope.metadata.get("protocol_validation"),
                    "delivery_results": [item.metadata for item in report.delivery_results],
                },
                ensure_ascii=False,
            )
        )
    except AppError as exc:
        print(json.dumps({"case": name, "ok": False, "error_code": exc.code, "message": str(exc)}, ensure_ascii=False))


async def main() -> None:
    if LOG_PATH.exists():
        LOG_PATH.unlink()

    await send_case(
        "pass",
        group_id="channel-alpha",
        message_type="message.posted",
        payload={"text": "normal collaboration message"},
        actor_agent_id="agent-source",
        target_agent_id="agent-target",
        thread_id="thread-001",
    )
    await send_case(
        "warn",
        group_id="channel-alpha",
        message_type="message.posted",
        payload={"text": "message without explicit target"},
        actor_agent_id="agent-source",
        target_agent_id=None,
        thread_id="thread-002",
    )
    await send_case(
        "reroute_suggest",
        group_id="channel-alpha",
        message_type="message.posted",
        payload={"text": "please move this wrong-channel discussion", "marker": "wrong-channel"},
        actor_agent_id="agent-source",
        target_agent_id="agent-target",
        thread_id="thread-003",
    )
    await send_case(
        "block",
        group_id="",
        message_type="message.posted",
        payload={"text": "message missing channel"},
        actor_agent_id="agent-source",
        target_agent_id="agent-target",
        thread_id="thread-004",
    )

    print(f"log_path={LOG_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
