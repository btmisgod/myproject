from __future__ import annotations

from app.services.message_envelope import DeliveryTarget, MessageEnvelope, RoutingPlan


# Community-side routing skeleton.
# The router decides who should receive a message bus envelope, but this phase
# only establishes the interface and minimal default routing behavior.


ROUTE_TYPES = (
    "direct",
    "channel",
    "broadcast",
    "system",
)


def resolve_route_type(envelope: MessageEnvelope) -> str:
    if envelope.target and envelope.target.target_scope == "agent" and envelope.target.target_agent_id:
        return "direct"
    if envelope.category == "broadcast_message" or (envelope.target and envelope.target.target_scope == "broadcast"):
        return "broadcast"
    if envelope.category == "system_event" or (envelope.target and envelope.target.target_scope == "system"):
        return "system"
    return "channel"


def build_direct_targets(envelope: MessageEnvelope) -> list[DeliveryTarget]:
    if not envelope.target or not envelope.target.target_agent_id:
        return []
    return [
        DeliveryTarget(
            target_type="agent",
            target_id=envelope.target.target_agent_id,
            group_id=envelope.channel_id,
            metadata={"mode": "direct_target"},
        )
    ]


def build_channel_targets(envelope: MessageEnvelope) -> list[DeliveryTarget]:
    return [
        DeliveryTarget(
            target_type="channel_members",
            target_id=envelope.channel_id,
            group_id=envelope.channel_id,
            metadata={"mode": "channel_fanout"},
        )
    ]


def build_broadcast_targets(envelope: MessageEnvelope) -> list[DeliveryTarget]:
    return [
        DeliveryTarget(
            target_type="broadcast",
            target_id=envelope.channel_id,
            group_id=envelope.channel_id,
            metadata={"mode": "broadcast_fanout"},
        )
    ]


def build_system_targets(envelope: MessageEnvelope) -> list[DeliveryTarget]:
    return [
        DeliveryTarget(
            target_type="system_handler",
            target_id=envelope.event_type,
            group_id=envelope.channel_id,
            metadata={"mode": "internal_system_handler"},
        )
    ]


def route_envelope(envelope: MessageEnvelope) -> RoutingPlan:
    route_type = resolve_route_type(envelope)
    if route_type == "direct":
        targets = build_direct_targets(envelope)
    elif route_type == "broadcast":
        targets = build_broadcast_targets(envelope)
    elif route_type == "system":
        targets = build_system_targets(envelope)
    else:
        targets = build_channel_targets(envelope)

    return RoutingPlan(
        envelope=envelope,
        route_type=route_type,
        targets=targets,
        metadata={
            "router": "community.message_router",
            "phase": "skeleton",
            "protocol_validation_hook": "before_route",
        },
    )
