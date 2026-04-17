import pytest

from app.services.delivery_adapter import DeliveryAdapter
from app.services.event_dispatcher import EventDispatcher
from app.services.message_bus import CommunityMessageBus
from app.services.message_envelope import DeliveryResult, DeliveryTarget, MessageEnvelope, MessageTarget
from app.services.protocol_validation_hook import ProtocolValidationHook


class MockDeliveryAdapter(DeliveryAdapter):
    def __init__(self) -> None:
        self.deliveries: list[tuple[MessageEnvelope, DeliveryTarget]] = []

    async def deliver(self, envelope: MessageEnvelope, target: DeliveryTarget) -> DeliveryResult:
        self.deliveries.append((envelope, target))
        return DeliveryResult(
            target=target,
            accepted=True,
            metadata={
                "seen_protocol_validation": envelope.metadata.get("protocol_validation"),
                "protocol_warning": envelope.metadata.get("protocol_warning"),
                "protocol_reroute_suggest": envelope.metadata.get("protocol_reroute_suggest"),
            },
        )


def make_bus(adapter: MockDeliveryAdapter) -> CommunityMessageBus:
    return CommunityMessageBus(
        hooks=[ProtocolValidationHook()],
        dispatcher=EventDispatcher(adapters=[adapter]),
    )


def make_envelope(
    *,
    group_id: str,
    payload: dict,
    target_agent_id: str | None = None,
    mentions: list | None = None,
) -> MessageEnvelope:
    return MessageEnvelope(
        message_id="msg-001",
        category="channel_message",
        event_type="message.posted",
        channel_id=group_id,
        payload=payload,
        priority="normal",
        timestamp="2026-03-18T00:00:00+00:00",
        source_agent="agent-source",
        target=MessageTarget(target_scope="agent", target_agent_id=target_agent_id) if target_agent_id else None,
        mentions=mentions or [],
        correlation_id="corr-001",
        thread_id="thread-001",
        metadata={},
    )


@pytest.mark.asyncio
async def test_protocol_validation_pass_routes_normally() -> None:
    adapter = MockDeliveryAdapter()
    bus = make_bus(adapter)
    envelope = make_envelope(
        group_id="group-alpha",
        payload={"text": "normal collaboration message"},
        target_agent_id="agent-target",
    )

    report = await bus.publish(envelope)

    assert report.routing_plan.route_type == "direct"
    assert len(adapter.deliveries) == 1
    delivered_envelope, _ = adapter.deliveries[0]
    assert delivered_envelope.metadata["protocol_validation"]["decision"] == "pass"
    assert "protocol_warning" not in delivered_envelope.metadata
    assert "protocol_reroute_suggest" not in delivered_envelope.metadata


@pytest.mark.asyncio
async def test_protocol_validation_channel_message_without_target_passes_normally() -> None:
    adapter = MockDeliveryAdapter()
    bus = make_bus(adapter)
    envelope = make_envelope(
        group_id="group-alpha",
        payload={"text": "message without explicit target"},
        target_agent_id=None,
    )

    report = await bus.publish(envelope)

    assert report.routing_plan.route_type == "channel"
    assert len(adapter.deliveries) == 1
    delivered_envelope, _ = adapter.deliveries[0]
    assert delivered_envelope.metadata["protocol_validation"]["decision"] == "pass"
    assert "protocol_warning" not in delivered_envelope.metadata


@pytest.mark.asyncio
async def test_protocol_validation_block_stops_before_delivery() -> None:
    adapter = MockDeliveryAdapter()
    with pytest.raises(ValueError, match="group_id is required for MessageEnvelope"):
        make_envelope(
            group_id="",
            payload={"text": "message missing group"},
            target_agent_id="agent-target",
        )
    assert adapter.deliveries == []


@pytest.mark.asyncio
async def test_protocol_validation_reroute_suggest_continues_and_marks_metadata() -> None:
    adapter = MockDeliveryAdapter()
    bus = make_bus(adapter)
    envelope = make_envelope(
        group_id="group-alpha",
        payload={"text": "please move this wrong-group collaboration", "marker": "wrong-group"},
        target_agent_id="agent-target",
    )

    report = await bus.publish(envelope)

    assert report.routing_plan.route_type == "direct"
    assert len(adapter.deliveries) == 1
    delivered_envelope, _ = adapter.deliveries[0]
    assert delivered_envelope.metadata["protocol_validation"]["decision"] == "reroute_suggest"
    assert delivered_envelope.metadata["protocol_validation"]["suggested_group_id"] == "suggested-group"
    assert delivered_envelope.metadata["protocol_reroute_suggest"] is True
