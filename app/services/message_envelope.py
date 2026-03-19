from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any


# Standard runtime envelope types for the Community Message Bus.
# These structures are community-internal transport contracts. They are not
# equivalent to agent persona prompts or model input formats.


MESSAGE_ENVELOPE_CATEGORIES = (
    "channel_message",
    "system_event",
    "broadcast_message",
    "protocol_reminder",
)

MESSAGE_ENVELOPE_PRIORITIES = (
    "low",
    "normal",
    "high",
    "urgent",
)

TARGET_SCOPES = (
    "agent",
    "group",
    "channel_members",
    "broadcast",
    "system",
)


@dataclass(frozen=True)
class MessageMention:
    mention_type: str
    mention_id: str
    display_text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MessageTarget:
    target_scope: str
    target_agent_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MessageEnvelope:
    # Required core fields for any envelope entering the Community Message Bus.
    message_id: str
    category: str
    event_type: str
    channel_id: str
    payload: dict[str, Any]
    priority: str
    timestamp: str
    # Optional routing and relationship fields.
    source_agent: str | None = None
    target: MessageTarget | None = None
    mentions: list[MessageMention] = field(default_factory=list)
    correlation_id: str | None = None
    thread_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DeliveryTarget:
    target_type: str
    target_id: str
    group_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RoutingPlan:
    envelope: MessageEnvelope
    route_type: str
    targets: list[DeliveryTarget] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DeliveryResult:
    target: DeliveryTarget
    accepted: bool
    metadata: dict[str, Any] = field(default_factory=dict)


def envelope_timestamp_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def message_envelope_schema() -> dict[str, Any]:
    # Equivalent JSON-schema style description for Message Bus producers and
    # downstream consumers. Validation can be added later without changing the
    # shape contract defined here.
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CommunityMessageEnvelope",
        "type": "object",
        "required": [
            "message_id",
            "category",
            "event_type",
            "channel_id",
            "payload",
            "priority",
            "timestamp",
        ],
        "properties": {
            "message_id": {"type": "string"},
            "category": {"type": "string", "enum": list(MESSAGE_ENVELOPE_CATEGORIES)},
            "event_type": {"type": "string"},
            "channel_id": {"type": "string"},
            "source_agent": {"type": ["string", "null"]},
            "target": {
                "type": ["object", "null"],
                "required": ["target_scope"],
                "properties": {
                    "target_scope": {"type": "string", "enum": list(TARGET_SCOPES)},
                    "target_agent_id": {"type": ["string", "null"]},
                    "metadata": {"type": "object"},
                },
                "additionalProperties": True,
            },
            "mentions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["mention_type", "mention_id"],
                    "properties": {
                        "mention_type": {"type": "string"},
                        "mention_id": {"type": "string"},
                        "display_text": {"type": ["string", "null"]},
                        "metadata": {"type": "object"},
                    },
                    "additionalProperties": True,
                },
            },
            "payload": {"type": "object"},
            "priority": {"type": "string", "enum": list(MESSAGE_ENVELOPE_PRIORITIES)},
            "timestamp": {"type": "string", "format": "date-time"},
            "correlation_id": {"type": ["string", "null"]},
            "thread_id": {"type": ["string", "null"]},
            "metadata": {"type": "object"},
        },
        "additionalProperties": False,
    }
