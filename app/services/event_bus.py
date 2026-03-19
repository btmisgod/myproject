import json
import logging
import hmac
import hashlib
import uuid
from collections.abc import AsyncIterator
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

logger = logging.getLogger(__name__)

redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
console_projector = ConsoleProjector()
web_projector = WebProjector()


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


async def publish_event(event: Event) -> None:
    projection = web_projector.to_publishable(event)
    payload_json = projection.model_dump_json()
    await redis_client.publish(group_stream_channel(event.group_id), projection.model_dump_json())
    await deliver_group_webhooks(event.group_id, payload_json)
    await deliver_agent_webhooks(event.group_id, payload_json)
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


async def deliver_agent_webhooks(group_id: uuid.UUID, payload_json: str) -> None:
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
                        "X-Community-Delivery-Mode": "agent_membership",
                    },
                )
                logger.info(
                    "agent_webhook_delivered",
                    extra={
                        "group_id": str(group_id),
                        "agent_id": str(subscription.agent_id),
                        "target_url": subscription.target_url,
                        "status_code": response.status_code,
                    },
                )
            except Exception as exc:
                logger.warning(
                    "agent_webhook_delivery_failed",
                    extra={
                        "group_id": str(group_id),
                        "agent_id": str(subscription.agent_id),
                        "target_url": subscription.target_url,
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
