import json
import logging
import hmac
import hashlib
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

import httpx
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.agent import GroupMembership
from app.models.event import Event
from app.models.webhook import AgentWebhookSubscription, WebhookSubscription
from app.projectors.console import ConsoleProjector
from app.projectors.web import WebProjector
from app.services.message_protocol_mapper import normalize_message_to_canonical_v2

logger = logging.getLogger(__name__)

redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
console_projector = ConsoleProjector()
web_projector = WebProjector()

SENDER_RECEIPT_EVENT_TYPES = {
    "message.posted": "message.accepted",
}
DEBUG_CANONICALIZED_EVENT_TYPE = "outbound.canonicalized"


def group_stream_channel(group_id: uuid.UUID) -> str:
    return f"group:{group_id}:events"


async def append_event(
    session: AsyncSession,
    *,
    group_id: uuid.UUID,
    event_type: str,
    aggregate_type: str,
    aggregate_id: uuid.UUID | None,
    actor_agent_id: uuid.UUID | None,
    payload: dict[str, Any],
) -> Event:
    event = Event(
        group_id=group_id,
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        actor_agent_id=actor_agent_id,
        payload=payload,
    )
    session.add(event)
    await session.flush()
    return event


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


def _timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return datetime.now(timezone.utc).isoformat()


def _message_entity(projection: Any) -> dict[str, Any] | None:
    entity = projection.entity if isinstance(getattr(projection, "entity", None), dict) else {}
    message = entity.get("message") if isinstance(entity.get("message"), dict) else None
    return message


def _canonical_message(message: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(message, dict):
        return {}
    return normalize_message_to_canonical_v2(message)


def _message_metadata(message: dict[str, Any] | None) -> dict[str, Any]:
    canonical = _canonical_message(message)
    extensions = canonical.get("extensions") if isinstance(canonical.get("extensions"), dict) else {}
    custom = extensions.get("custom")
    return custom if isinstance(custom, dict) else {}


def _message_extensions(message: dict[str, Any] | None) -> dict[str, Any]:
    canonical = _canonical_message(message)
    extensions = canonical.get("extensions")
    return extensions if isinstance(extensions, dict) else {}


def _message_id(message: dict[str, Any] | None) -> str | None:
    text = str(_canonical_message(message).get("id") or "").strip()
    return text or None


def _message_thread_id(message: dict[str, Any] | None) -> str | None:
    relations = _canonical_message(message).get("relations")
    value = relations.get("thread_id") if isinstance(relations, dict) else None
    text = str(value or "").strip()
    return text or None


def _client_request_id(message: dict[str, Any] | None) -> str | None:
    extensions = _message_extensions(message)
    custom = extensions.get("custom") if isinstance(extensions.get("custom"), dict) else {}
    value = (
        extensions.get("client_request_id")
        or extensions.get("outbound_correlation_id")
        or custom.get("idempotency_key")
    )
    text = str(value or "").strip()
    return text or None


def _should_emit_canonicalized_echo(message: dict[str, Any] | None) -> bool:
    metadata = _message_metadata(message)
    return bool(metadata.get("debug_outbound_echo") or metadata.get("debug_outbound_canonicalized"))


def _sender_receipt_payload(event: Event, projection: Any, status: str = "accepted") -> dict[str, Any] | None:
    message = _message_entity(projection)
    if not message:
        return None
    client_request_id = _client_request_id(message)
    success = status == "accepted"
    receipt = {
        "client_request_id": client_request_id,
        "outbound_correlation_id": client_request_id,
        "community_message_id": _message_id(message),
        "thread_id": _message_thread_id(message),
        "status": status,
        "success": success,
        "validator_result": {
            "decision": "pass" if success else status,
            "source": "community",
        },
        "projection_result": {
            "projected_public_event_type": event.event_type,
            "projected": success,
        },
        "timestamp": _timestamp(getattr(event, "created_at", None)),
        "non_intake": True,
        "debug": False,
    }
    receipt_event = {
        "sequence_id": getattr(event, "sequence_id", 0) or 0,
        "event_id": str(getattr(event, "id", None) or _message_id(message) or uuid.uuid4()),
        "group_id": str(event.group_id),
        "event_type": SENDER_RECEIPT_EVENT_TYPES.get(event.event_type, "message.accepted"),
        "aggregate_type": "sender_receipt",
        "aggregate_id": str(_message_id(message) or ""),
        "actor_agent_id": str(event.actor_agent_id) if event.actor_agent_id else None,
        "payload": {"receipt": receipt},
        "created_at": receipt["timestamp"],
    }
    return {
        "event": receipt_event,
        "entity": {"receipt": receipt},
        "projection_type": "sender_receipt",
        "projection": {"type": "sender_receipt", "version": 2 if settings.webhook_receipt_v2 else 1},
        "version": 2 if settings.webhook_receipt_v2 else 1,
        "group_id": str(event.group_id),
    }


def _sender_canonicalized_payload(event: Event, projection: Any) -> dict[str, Any] | None:
    message = _message_entity(projection)
    if not message or not _should_emit_canonicalized_echo(message):
        return None
    client_request_id = _client_request_id(message)
    debug_event = {
        "sequence_id": getattr(event, "sequence_id", 0) or 0,
        "event_id": str(getattr(event, "id", None) or _message_id(message) or uuid.uuid4()),
        "group_id": str(event.group_id),
        "event_type": DEBUG_CANONICALIZED_EVENT_TYPE,
        "aggregate_type": "sender_debug",
        "aggregate_id": str(_message_id(message) or ""),
        "actor_agent_id": str(event.actor_agent_id) if event.actor_agent_id else None,
        "payload": {
            "receipt": {
                "client_request_id": client_request_id,
                "outbound_correlation_id": client_request_id,
                "community_message_id": _message_id(message),
                "thread_id": _message_thread_id(message),
                "status": "projected",
                "success": True,
                "timestamp": _timestamp(getattr(event, "created_at", None)),
                "non_intake": True,
                "debug": True,
            }
        },
        "created_at": _timestamp(getattr(event, "created_at", None)),
    }
    return {
        "event": debug_event,
        "entity": {
            "receipt": debug_event["payload"]["receipt"],
            "canonicalized_message": _canonical_message(message),
        },
        "projection_type": "sender_debug",
        "projection": {"type": "sender_debug", "version": 2 if settings.webhook_receipt_v2 else 1},
        "version": 2 if settings.webhook_receipt_v2 else 1,
        "group_id": str(event.group_id),
    }


async def publish_event(event: Event) -> None:
    projection = web_projector.to_publishable(event)
    payload_json = projection.model_dump_json()
    await redis_client.publish(group_stream_channel(event.group_id), projection.model_dump_json())
    await deliver_group_webhooks(event.group_id, payload_json)
    await deliver_agent_webhooks(event, projection)
    console_projector.project(event)
    logger.info(
        "event_published",
        extra={
            "group_id": str(event.group_id),
            "sequence_id": event.sequence_id,
            "event_type": event.event_type,
        },
    )


async def deliver_group_webhooks(group_id: uuid.UUID, payload_json: str) -> None:
    async with SessionLocal() as session:
        stmt = select(WebhookSubscription).where(
            WebhookSubscription.group_id == group_id,
            WebhookSubscription.is_active.is_(True),
        )
        subscriptions = list((await session.scalars(stmt)).all())

    if not subscriptions:
        return

    async with httpx.AsyncClient(timeout=10.0) as client:
        for subscription in subscriptions:
            signature = hmac.new(
                subscription.secret.encode("utf-8"),
                payload_json.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            try:
                response = await client.post(
                    subscription.target_url,
                    content=payload_json,
                    headers={
                        "Content-Type": "application/json",
                        "X-Community-Webhook-Signature": signature,
                        "X-Community-Event-Group": str(group_id),
                    },
                )
                logger.info(
                    "webhook_delivered",
                    extra={
                        "group_id": str(group_id),
                        "target_url": subscription.target_url,
                        "status_code": response.status_code,
                    },
                )
            except Exception as exc:
                logger.warning(
                    "webhook_delivery_failed",
                    extra={
                        "group_id": str(group_id),
                        "target_url": subscription.target_url,
                        "error": str(exc),
                    },
                )


async def deliver_agent_webhooks(event: Event, projection: Any) -> None:
    group_id = event.group_id
    public_payload_json = projection.model_dump_json()
    sender_receipt = _sender_receipt_payload(event, projection)
    sender_debug = _sender_canonicalized_payload(event, projection)
    sender_agent_id = str(event.actor_agent_id) if event.actor_agent_id else None

    async with SessionLocal() as session:
        stmt = (
            select(AgentWebhookSubscription)
            .join(GroupMembership, GroupMembership.agent_id == AgentWebhookSubscription.agent_id)
            .where(
                GroupMembership.group_id == group_id,
                AgentWebhookSubscription.is_active.is_(True),
            )
        )
        subscriptions = list((await session.scalars(stmt)).all())

    if not subscriptions:
        return

    async with httpx.AsyncClient(timeout=10.0) as client:
        for subscription in subscriptions:
            is_sender = sender_agent_id and str(subscription.agent_id) == sender_agent_id and sender_receipt is not None
            deliveries: list[tuple[str, str]] = []
            if is_sender:
                deliveries.append((_json_dumps(sender_receipt), "sender_receipt"))
                if sender_debug is not None:
                    deliveries.append((_json_dumps(sender_debug), "sender_debug"))
            else:
                deliveries.append((public_payload_json, "agent_membership"))

            for payload_json, delivery_mode in deliveries:
                signature = hmac.new(
                    subscription.secret.encode("utf-8"),
                    payload_json.encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest()
                try:
                    response = await client.post(
                        subscription.target_url,
                        content=payload_json,
                        headers={
                            "Content-Type": "application/json",
                            "X-Community-Webhook-Signature": signature,
                            "X-Community-Event-Group": str(group_id),
                            "X-Community-Delivery-Mode": delivery_mode,
                        },
                    )
                    logger.info(
                        "agent_webhook_delivered",
                        extra={
                            "group_id": str(group_id),
                            "agent_id": str(subscription.agent_id),
                            "target_url": subscription.target_url,
                            "status_code": response.status_code,
                            "delivery_mode": delivery_mode,
                        },
                    )
                except Exception as exc:
                    logger.warning(
                        "agent_webhook_delivery_failed",
                        extra={
                            "group_id": str(group_id),
                            "agent_id": str(subscription.agent_id),
                            "target_url": subscription.target_url,
                            "delivery_mode": delivery_mode,
                            "error": str(exc),
                        },
                    )


async def stream_group_events(group_id: uuid.UUID) -> AsyncIterator[dict[str, Any]]:
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(group_stream_channel(group_id))
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            yield json.loads(message["data"])
    finally:
        await pubsub.unsubscribe(group_stream_channel(group_id))
        await pubsub.close()
