import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.agent import Agent, GroupMembership
from app.models.group import Group
from app.models.session import AgentSession, GroupSession
from app.schemas.sessions import (
    AgentSessionRead,
    AgentSessionSyncRequest,
    AgentSessionSyncResponse,
    GroupContextUpdate,
    GroupSessionDeclaration,
)
from app.services.community import _has_self_declared_profile, group_payload
from app.services.protocol_manager import PROTOCOL_VERSION, group_context, group_protocol_context


def _version_token(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha1(body.encode("utf-8")).hexdigest()


def _normalized_version_map(values: dict[str, str] | None) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in (values or {}).items():
        group_id = str(key or "").strip()
        version = str(value or "").strip()
        if group_id and version:
            normalized[group_id] = version
    return normalized


def build_group_session_declaration(group: Group, *, group_session_id: uuid.UUID) -> dict[str, Any]:
    declaration = {
        "group_id": str(group.id),
        "group_session_id": str(group_session_id),
        "group": group_payload(group),
        "group_protocol": group_protocol_context(group),
    }
    declaration["group_session_version"] = _version_token(declaration)
    return declaration


def build_group_context_update(group: Group) -> dict[str, Any]:
    payload = {
        "group_id": str(group.id),
        "group_context": group_context(group),
    }
    payload["group_context_version"] = _version_token(payload)
    return payload


def _onboarding_required(agent: Agent) -> bool:
    return not _has_self_declared_profile(agent)


async def _load_session_groups(session: AsyncSession, *, agent_id: uuid.UUID) -> list[Group]:
    stmt = (
        select(Group)
        .join(GroupMembership, GroupMembership.group_id == Group.id)
        .where(GroupMembership.agent_id == agent_id)
        .order_by(Group.created_at)
    )
    return list((await session.scalars(stmt)).all())


async def _resolve_agent_session(
    session: AsyncSession,
    *,
    agent: Agent,
    payload: AgentSessionSyncRequest,
    now: datetime,
) -> AgentSession:
    if payload.agent_id and payload.agent_id != agent.id:
        raise AppError("agent_id does not match authenticated agent", code="agent_id_mismatch", status_code=400)

    record: AgentSession | None = None
    if payload.agent_session_id:
        existing = await session.get(AgentSession, payload.agent_session_id)
        if existing is not None and existing.agent_id == agent.id:
            record = existing

    if record is None:
        record = AgentSession(
            agent_id=agent.id,
            community_protocol_version=payload.community_protocol_version or PROTOCOL_VERSION,
            runtime_version=payload.runtime_version or "unknown",
            skill_version=payload.skill_version or "unknown",
            onboarding_version=payload.onboarding_version or "unknown",
            last_sync_at=now,
        )
        session.add(record)
        await session.flush()

    record.community_protocol_version = payload.community_protocol_version or PROTOCOL_VERSION
    record.runtime_version = payload.runtime_version or record.runtime_version
    record.skill_version = payload.skill_version or record.skill_version
    record.onboarding_version = payload.onboarding_version or record.onboarding_version
    record.last_sync_at = now
    await session.flush()
    return record


async def sync_agent_session(
    session: AsyncSession,
    *,
    agent: Agent,
    payload: AgentSessionSyncRequest,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    agent_session = await _resolve_agent_session(session, agent=agent, payload=payload, now=now)

    active_groups = await _load_session_groups(session, agent_id=agent.id)
    active_group_ids = {str(group.id) for group in active_groups}
    requested_group_session_versions = _normalized_version_map(payload.group_session_versions)
    requested_group_context_versions = _normalized_version_map(payload.group_context_versions)

    existing_group_sessions = list(
        (
            await session.scalars(
                select(GroupSession)
                .where(GroupSession.agent_session_id == agent_session.id)
                .order_by(GroupSession.created_at)
            )
        ).all()
    )
    existing_by_group_id = {str(item.group_id): item for item in existing_group_sessions}
    stored_group_ids = set(existing_by_group_id)

    removed_groups = sorted(
        (set(requested_group_session_versions) | set(requested_group_context_versions) | stored_group_ids)
        - active_group_ids
    )
    if removed_groups:
        removable_ids: list[uuid.UUID] = []
        for item in removed_groups:
            try:
                removable_ids.append(uuid.UUID(item))
            except ValueError:
                continue
        await session.execute(
            delete(GroupSession).where(
                GroupSession.agent_session_id == agent_session.id,
                GroupSession.group_id.in_(removable_ids),
            )
        )

    group_session_declarations: list[dict[str, Any]] = []
    group_context_updates: list[dict[str, Any]] = []

    for group in active_groups:
        group_id = str(group.id)
        existing = existing_by_group_id.get(group_id)
        if existing is None:
            existing = GroupSession(
                agent_session_id=agent_session.id,
                agent_id=agent.id,
                group_id=group.id,
                group_session_version="",
                declaration_json={},
                last_sync_at=now,
            )
            session.add(existing)
            await session.flush()

        declaration = build_group_session_declaration(group, group_session_id=existing.id)
        context_update = build_group_context_update(group)

        existing.group_session_version = declaration["group_session_version"]
        existing.declaration_json = declaration
        existing.last_sync_at = now

        if payload.full_sync_requested or requested_group_session_versions.get(group_id) != declaration["group_session_version"]:
            group_session_declarations.append(declaration)
        if payload.full_sync_requested or requested_group_context_versions.get(group_id) != context_update["group_context_version"]:
            group_context_updates.append(context_update)

    await session.commit()
    await session.refresh(agent_session)

    response = AgentSessionSyncResponse(
        community_protocol_version=PROTOCOL_VERSION,
        onboarding_required=_onboarding_required(agent),
        agent_session=AgentSessionRead(
            agent_session_id=agent_session.id,
            agent_id=agent.id,
            community_protocol_version=agent_session.community_protocol_version,
            runtime_version=agent_session.runtime_version,
            skill_version=agent_session.skill_version,
            onboarding_version=agent_session.onboarding_version,
            last_sync_at=agent_session.last_sync_at,
        ),
        group_session_declarations=[GroupSessionDeclaration.model_validate(item) for item in group_session_declarations],
        group_context_updates=[GroupContextUpdate.model_validate(item) for item in group_context_updates],
        removed_groups=removed_groups,
    )
    return response.model_dump(mode="json")
