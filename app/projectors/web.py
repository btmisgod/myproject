from typing import Any

from app.schemas.common import EventEnvelope
from app.schemas.projection import PublishableProjection


class WebProjector:
    name = "web"

    def to_publishable(self, event: dict[str, Any]) -> PublishableProjection:
        entity = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        envelope = EventEnvelope(
            sequence_id=int(event.get("sequence_id") or 0),
            event_id=event.get("event_id"),
            group_id=event.get("group_id"),
            event_type=str(event.get("event_type") or ""),
            aggregate_type=str(event.get("aggregate_type") or ""),
            aggregate_id=event.get("aggregate_id"),
            actor_agent_id=event.get("actor_agent_id"),
            payload=entity,
            created_at=event.get("created_at"),
        )
        message = entity.get("message") if isinstance(entity.get("message"), dict) else None
        delivery_scope = {
            "scope": "group_context" if str(event.get("event_type") or "") == "broadcast.delivered" else "group",
            "group_id": str(envelope.group_id),
        }
        return PublishableProjection(
            event=envelope,
            entity=entity,
            group_id=envelope.group_id,
            version=2,
            occurred_at=envelope.created_at,
            delivery_scope=delivery_scope,
            message=message,
        )

