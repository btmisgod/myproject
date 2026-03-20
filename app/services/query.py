import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent, GroupMembership, Presence
from app.models.event import Event
from app.models.group import Group
from app.models.message import Message
from app.models.task import Task
from app.models.webhook import AgentWebhookSubscription, WebhookSubscription
from app.services.message_protocol_mapper import serialize_summary_v2


async def list_agents(session: AsyncSession) -> list[Agent]:
    return list((await session.scalars(select(Agent).order_by(Agent.created_at))).all())


async def list_groups(session: AsyncSession) -> list[Group]:
    return list((await session.scalars(select(Group).order_by(Group.created_at))).all())


async def list_group_memberships(session: AsyncSession, group_id: uuid.UUID) -> list[GroupMembership]:
    stmt = select(GroupMembership).where(GroupMembership.group_id == group_id).order_by(GroupMembership.created_at)
    return list((await session.scalars(stmt)).all())


async def list_group_agents(session: AsyncSession, group_id: uuid.UUID) -> list[Agent]:
    stmt = (
        select(Agent)
        .join(GroupMembership, GroupMembership.agent_id == Agent.id)
        .where(GroupMembership.group_id == group_id)
        .order_by(Agent.created_at)
    )
    return list((await session.scalars(stmt)).all())


async def list_messages(
    session: AsyncSession,
    *,
    group_id: uuid.UUID,
    thread_id: uuid.UUID | None = None,
    task_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
    newest_first: bool = False,
) -> list[Message]:
    stmt = select(Message).where(Message.group_id == group_id)
    if thread_id:
        stmt = stmt.where(Message.thread_id == thread_id)
    if task_id:
        stmt = stmt.where(Message.task_id == task_id)
    order_clause = desc(Message.created_at) if newest_first else Message.created_at
    stmt = stmt.order_by(order_clause).limit(limit).offset(offset)
    return list((await session.scalars(stmt)).all())


async def list_tasks(session: AsyncSession, *, group_id: uuid.UUID) -> list[Task]:
    stmt = select(Task).where(Task.group_id == group_id).order_by(Task.created_at)
    return list((await session.scalars(stmt)).all())


async def list_presence(session: AsyncSession, *, group_id: uuid.UUID) -> list[Presence]:
    stmt = select(Presence).where(Presence.group_id == group_id).order_by(Presence.updated_at.desc())
    return list((await session.scalars(stmt)).all())


async def list_events(
    session: AsyncSession,
    *,
    group_id: uuid.UUID,
    after_sequence: int | None = None,
    limit: int = 100,
) -> list[Event]:
    stmt = select(Event).where(Event.group_id == group_id)
    if after_sequence is not None:
        stmt = stmt.where(Event.sequence_id > after_sequence)
    stmt = stmt.order_by(Event.sequence_id).limit(limit)
    return list((await session.scalars(stmt)).all())


async def latest_host_summary(session: AsyncSession, *, group_id: uuid.UUID) -> dict[str, object]:
    stmt = (
        select(Message)
        .where(Message.group_id == group_id, Message.message_type == "summary")
        .order_by(desc(Message.created_at))
        .limit(1)
    )
    message = (await session.scalars(stmt)).first()
    return serialize_summary_v2(message)


async def list_webhook_subscriptions(
    session: AsyncSession,
    *,
    group_id: uuid.UUID,
) -> list[WebhookSubscription]:
    stmt = (
        select(WebhookSubscription)
        .where(WebhookSubscription.group_id == group_id)
        .order_by(WebhookSubscription.created_at)
    )
    return list((await session.scalars(stmt)).all())


async def list_agent_webhook_subscriptions(session: AsyncSession) -> list[AgentWebhookSubscription]:
    stmt = select(AgentWebhookSubscription).order_by(AgentWebhookSubscription.created_at)
    return list((await session.scalars(stmt)).all())
