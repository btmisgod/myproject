import logging
import hashlib
import re
import uuid
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.security import generate_agent_token, hash_token
from app.models.agent import Agent, GroupMembership, Presence
from app.models.enums import EventType, FlowType, MessageType, PresenceState, TaskStatus
from app.models.event import Event
from app.models.group import Group
from app.models.message import Message
from app.models.task import Task
from app.models.webhook import AgentWebhookSubscription, WebhookSubscription
from app.schemas.agents import AgentCreate, AgentProfileUpdateRequest
from app.schemas.groups import GroupCreate
from app.schemas.messages import MessageCreate
from app.schemas.presence import PresenceUpdateRequest
from app.schemas.tasks import (
    TaskClaimRequest,
    TaskCreate,
    TaskHandoffRequest,
    TaskResultSummaryRequest,
    TaskStatusUpdateRequest,
)
from app.schemas.webhooks import WebhookSubscriptionCreate
from app.services.channel_protocol_binding import COMMUNITY_PROTOCOLS_KEY
from app.services.event_bus import append_event, publish_event
from app.services.message_envelope import MessageEnvelope, MessageMention, MessageTarget, envelope_timestamp_now
from app.services.message_protocol_mapper import normalize_message_to_canonical_v2, serialize_message_v2
from app.services.protocol_validation_hook import _deliver_protocol_violation_feedback, _load_channel_protocol_context
from app.services.protocol_manager import PROFILE_RULE_ID, PROTOCOL_VERSION, agent_protocol_context, current_protocol_document, ensure_group_protocol_metadata, group_context, group_protocol_context, update_group_protocol_metadata
from app.services.protocol_validator import build_validation_request, validate_protocol_request

logger = logging.getLogger(__name__)


def _principal_agent(actor: Any) -> Agent:
    return getattr(actor, "agent", actor)


def _is_admin_protocol_exempt(actor: Any) -> bool:
    if getattr(actor, "actor_type", None) == "admin_user":
        return True
    principal = _principal_agent(actor)
    metadata = dict(getattr(principal, "metadata_json", {}) or {})
    return metadata.get("kind") == "human_admin"


def _slug_handle(value: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-_")
    return base[:32] or f"agent-{hashlib.sha1(value.encode('utf-8')).hexdigest()[:6]}"


def _profile_color(seed: str) -> str:
    palette = ["#C96B2C", "#0F766E", "#2563EB", "#7C3AED", "#BE123C", "#1D4ED8", "#1E7A59", "#B45309"]
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    return palette[int(digest[:2], 16) % len(palette)]


def _default_agent_profile(name: str, description: str | None, is_moderator: bool) -> dict[str, Any]:
    clean_name = name.strip()
    handle = _slug_handle(clean_name)
    # Community does not assign public collaboration identities by default.
    # Keep the generated profile neutral even if legacy moderator flags remain.
    title = "协作 Agent"
    return {
        "display_name": clean_name,
        "handle": handle,
        "identity": title,
        "tagline": description or f"{clean_name} 已接入社区协作总线。",
        "bio": description or f"{clean_name} 是社区中的 {title}，在公开群组内参与协作。",
        "avatar_text": clean_name[:2].upper(),
        "accent_color": _profile_color(clean_name),
        "expertise": [],
        "home_group_slug": None,
    }


def _normalized_profile(defaults: dict[str, Any], incoming: dict[str, Any] | None) -> dict[str, Any]:
    profile = {**defaults, **(incoming or {})}
    handle = str(profile.get("handle") or "").strip().lstrip("@")
    profile["handle"] = _slug_handle(handle or str(profile.get("display_name") or defaults["display_name"]))
    profile["display_name"] = str(profile.get("display_name") or defaults["display_name"]).strip()[:120]
    profile["identity"] = str(profile.get("identity") or defaults["identity"]).strip()[:80]
    profile["tagline"] = str(profile.get("tagline") or defaults["tagline"]).strip()[:160]
    profile["bio"] = str(profile.get("bio") or defaults["bio"]).strip()[:500]
    profile["avatar_text"] = str(profile.get("avatar_text") or defaults["avatar_text"]).strip()[:8]
    profile["accent_color"] = str(profile.get("accent_color") or defaults["accent_color"]).strip()[:20]
    expertise = profile.get("expertise") if isinstance(profile.get("expertise"), list) else []
    profile["expertise"] = [str(item).strip()[:32] for item in expertise if str(item).strip()][:12]
    home_group_slug = profile.get("home_group_slug")
    profile["home_group_slug"] = str(home_group_slug).strip()[:120] if home_group_slug else None
    return profile


def _community_agent_metadata(existing: dict[str, Any] | None, *, profile_completed: bool) -> dict[str, Any]:
    metadata = dict(existing or {})
    community = metadata.get("community") if isinstance(metadata.get("community"), dict) else {}
    community["profile_completed"] = profile_completed
    community["profile_rule_id"] = PROFILE_RULE_ID
    community["protocol_version"] = PROTOCOL_VERSION
    metadata["community"] = community
    return metadata


def _has_self_declared_profile(agent: Agent) -> bool:
    metadata = dict(agent.metadata_json or {})
    community_meta = metadata.get("community")
    if isinstance(community_meta, dict) and community_meta.get("profile_completed") is True:
        return True

    profile = metadata.get("profile")
    if not isinstance(profile, dict):
        return False

    defaults = _default_agent_profile(agent.name, agent.description, agent.is_moderator)
    normalized = _normalized_profile(defaults, profile)
    if normalized.get("handle") != defaults.get("handle"):
        return True
    for field in ("display_name", "identity", "tagline", "bio", "avatar_text", "accent_color"):
        if normalized.get(field) != defaults.get(field):
            return True
    if normalized.get("expertise") or normalized.get("home_group_slug"):
        return True
    return False


def ensure_agent_protocol_ready(actor: Any) -> None:
    if _is_admin_protocol_exempt(actor):
        return
    agent = _principal_agent(actor)
    if _has_self_declared_profile(agent):
        return
    raise AppError(
        "agent must self-declare profile before collaborating in the community. Use PATCH /api/v1/agents/me/profile to set your profile.",
        code="protocol_profile_required",
        status_code=403,
    )


def _message_mentions_from_payload(payload: dict[str, Any] | None) -> list[MessageMention]:
    if not isinstance(payload, dict):
        return []
    routing = payload.get("routing") if isinstance(payload.get("routing"), dict) else {}
    content = payload.get("content") if isinstance(payload.get("content"), dict) else {}
    metadata = content.get("metadata") if isinstance(content.get("metadata"), dict) else {}
    raw_mentions = routing.get("mentions")
    if not isinstance(raw_mentions, list):
        raw_mentions = content.get("mentions")
    if not isinstance(raw_mentions, list):
        raw_mentions = metadata.get("mentions")
    if not isinstance(raw_mentions, list):
        return []
    mentions: list[MessageMention] = []
    for item in raw_mentions:
        if not isinstance(item, dict):
            continue
        mention_id = str(item.get("mention_id") or "").strip()
        mention_type = str(item.get("mention_type") or "").strip()
        if not mention_id or not mention_type:
            continue
        mentions.append(
            MessageMention(
                mention_type=mention_type,
                mention_id=mention_id,
                display_text=item.get("display_text"),
                metadata=item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
            )
        )
    return mentions


def _message_target_from_payload(payload: dict[str, Any] | None) -> MessageTarget | None:
    if not isinstance(payload, dict):
        return None
    routing = payload.get("routing") if isinstance(payload.get("routing"), dict) else {}
    target = routing.get("target") if isinstance(routing.get("target"), dict) else {}
    content = payload.get("content") if isinstance(payload.get("content"), dict) else {}
    metadata = content.get("metadata") if isinstance(content.get("metadata"), dict) else {}
    target_agent_id = str(target.get("agent_id") or metadata.get("target_agent_id") or "").strip()
    if not target_agent_id:
        return None
    return MessageTarget(target_scope="agent", target_agent_id=target_agent_id)


async def _validate_protocol_action(
    *,
    action_type: str,
    actor: Any,
    group: Group,
    payload: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    # Skeleton hook for community-owned protocol validation.
    # Enforcement can become stricter later without moving logic into agents.
    principal = _principal_agent(actor)
    validation_context = dict(context or {})
    validation_context.update(await _load_channel_protocol_context(str(group.id)))
    result = validate_protocol_request(
        build_validation_request(
            action_type=action_type,
            actor_id=str(principal.id),
            group_id=str(group.id),
            payload=payload,
            context=validation_context,
        )
    )
    if result.decision == "block":
        first = result.issues[0]
        logger.warning(
            "protocol_validation_blocked_at_ingress",
            extra={
                "action_type": action_type,
                "group_id": str(group.id),
                "actor_id": str(principal.id),
                "violation_type": first.code,
            },
        )
        if action_type == "message.post" and isinstance(payload, dict):
            envelope = MessageEnvelope(
                message_id=str(uuid.uuid4()),
                category="channel_message",
                event_type="message.posted",
                channel_id=str(group.id),
                payload=payload,
                priority="normal",
                timestamp=envelope_timestamp_now(),
                source_agent=str(principal.id),
                target=_message_target_from_payload(payload),
                mentions=_message_mentions_from_payload(payload),
                thread_id=(
                    str(
                        (
                            payload.get("relations").get("thread_id")
                            if isinstance(payload.get("relations"), dict)
                            else payload.get("thread_id")
                        )
                        or ""
                    )
                    or None
                ),
            )
            await _deliver_protocol_violation_feedback(envelope=envelope, result=result)
        raise AppError(first.message, code=first.code, status_code=403)


def _effective_group_metadata(group: Group) -> dict[str, Any]:
    return ensure_group_protocol_metadata(group.metadata_json, group_name=group.name, group_slug=group.slug)


def _group_protocol_context(group: Group) -> dict[str, Any]:
    return group_protocol_context(group)


async def register_agent(session: AsyncSession, payload: AgentCreate) -> tuple[Agent, str]:
    existing = await session.scalar(select(Agent).where(Agent.name == payload.name))
    if existing:
        raise AppError("agent name already exists", code="agent_exists", status_code=409)

    token = generate_agent_token()
    metadata = dict(payload.metadata_json or {})
    defaults = _default_agent_profile(payload.name, payload.description, False)
    metadata["profile"] = _normalized_profile(defaults, metadata.get("profile"))
    metadata = _community_agent_metadata(metadata, profile_completed=False)
    agent = Agent(
        name=payload.name,
        description=payload.description,
        metadata_json=metadata,
        is_moderator=False,
        token_hash=hash_token(token),
    )
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent, token


async def update_agent_profile(
    session: AsyncSession,
    actor: Agent,
    payload: AgentProfileUpdateRequest,
) -> Agent:
    metadata = dict(actor.metadata_json or {})
    defaults = _default_agent_profile(actor.name, actor.description, actor.is_moderator)
    metadata["profile"] = _normalized_profile(defaults, payload.profile.model_dump(mode="json"))
    metadata = _community_agent_metadata(metadata, profile_completed=True)
    actor.metadata_json = metadata
    await session.commit()
    await session.refresh(actor)
    return actor


async def create_group(session: AsyncSession, payload: GroupCreate, actor: Agent) -> Group:
    existing = await session.scalar(select(Group).where(Group.slug == payload.slug))
    if existing:
        raise AppError("group slug already exists", code="group_exists", status_code=409)

    metadata = ensure_group_protocol_metadata(payload.metadata_json, group_name=payload.name, group_slug=payload.slug)
    group = Group(
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        group_type=payload.group_type.value,
        metadata_json=metadata,
    )
    session.add(group)
    await session.flush()

    membership = GroupMembership(group_id=group.id, agent_id=actor.id, role="member")
    presence = Presence(
        group_id=group.id,
        agent_id=actor.id,
        state=PresenceState.ONLINE.value,
    )
    session.add_all([membership, presence])
    event = await append_event(
        session,
        group_id=group.id,
        event_type=EventType.GROUP_CREATED.value,
        aggregate_type="group",
        aggregate_id=group.id,
        actor_agent_id=actor.id,
        payload={"group": group_payload(group)},
    )
    await session.commit()
    await session.refresh(group)
    await publish_event(event)
    return group


async def join_group(session: AsyncSession, group_id: uuid.UUID, actor: Agent) -> GroupMembership:
    group = await get_group_or_404(session, group_id)
    existing = await session.scalar(
        select(GroupMembership).where(
            GroupMembership.group_id == group.id,
            GroupMembership.agent_id == actor.id,
        )
    )
    if existing:
        return existing

    membership = GroupMembership(group_id=group.id, agent_id=actor.id, role="member")
    presence = Presence(group_id=group.id, agent_id=actor.id, state=PresenceState.ONLINE.value)
    session.add_all([membership, presence])
    event = await append_event(
        session,
        group_id=group.id,
        event_type=EventType.GROUP_JOINED.value,
        aggregate_type="membership",
        aggregate_id=membership.id,
        actor_agent_id=actor.id,
        payload={"agent_id": str(actor.id)},
    )
    await session.commit()
    await session.refresh(membership)
    await publish_event(event)
    return membership


async def post_message(session: AsyncSession, payload: MessageCreate, actor: Any) -> Message:
    principal = _principal_agent(actor)
    group = await get_group_or_404(session, payload.group_id)
    await ensure_membership(session, payload.group_id, principal.id)
    ensure_agent_protocol_ready(actor)
    canonical_message_v2 = normalize_message_to_canonical_v2(payload.model_dump(mode="json"))
    validation_payload = canonical_message_v2

    await _validate_protocol_action(
        action_type="message.post",
        actor=actor,
        group=group,
        payload=validation_payload,
    )

    resolved_parent_id, resolved_thread_id = await _resolve_message_relations(
        session,
        group_id=payload.group_id,
        parent_message_id=payload.parent_message_id,
        thread_id=payload.thread_id,
    )
    await _validate_target_agent(
        session,
        group_id=payload.group_id,
        routing=canonical_message_v2.get("routing"),
    )

    message = Message(
        group_id=payload.group_id,
        agent_id=principal.id,
        author_kind=canonical_message_v2.get("author_kind"),
        parent_message_id=resolved_parent_id,
        thread_id=resolved_thread_id,
        flow_type=canonical_message_v2["flow_type"],
        message_type=canonical_message_v2.get("message_type"),
        content=canonical_message_v2["content"],
        status_block_json=canonical_message_v2.get("status_block", {}),
        context_block_json=canonical_message_v2.get("context_block", {}),
        semantics_json={
            "flow_type": canonical_message_v2["flow_type"],
            "message_type": canonical_message_v2.get("message_type"),
        },
        routing_json=canonical_message_v2["routing"],
        extensions_json=canonical_message_v2.get("extensions", {}),
    )
    session.add(message)
    await session.flush()
    if message.thread_id is None:
        message.thread_id = message.id
        await session.flush()
    await session.refresh(message)

    event = await append_event(
        session,
        group_id=payload.group_id,
        event_type=EventType.MESSAGE_POSTED.value,
        aggregate_type="message",
        aggregate_id=message.id,
        actor_agent_id=principal.id,
        payload={"message": message_payload(message)},
    )
    await session.commit()
    await publish_event(event)
    return message


# These helpers currently preserve a group-scoped collaboration object workflow
# behind the historical Task persistence model. They should not be read as
# community-level task platform semantics.
async def create_task(session: AsyncSession, payload: TaskCreate, actor: Any) -> Task:
    principal = _principal_agent(actor)
    group = await get_group_or_404(session, payload.group_id)
    await ensure_membership(session, payload.group_id, principal.id)
    ensure_agent_protocol_ready(actor)
    await _validate_protocol_action(
        action_type="task.create",
        actor=actor,
        group=group,
        payload={
            "group_id": str(payload.group_id),
            "title": payload.title,
            "parent_task_id": str(payload.parent_task_id) if payload.parent_task_id else None,
            "metadata_json": payload.metadata_json,
        },
    )
    task = Task(
        group_id=payload.group_id,
        title=payload.title,
        description=payload.description,
        metadata_json=payload.metadata_json,
        parent_task_id=payload.parent_task_id,
        status=TaskStatus.PENDING.value,
    )
    session.add(task)
    await session.flush()
    task_event = await append_event(
        session,
        group_id=task.group_id,
        event_type=EventType.TASK_CREATED.value,
        aggregate_type="task",
        aggregate_id=task.id,
        actor_agent_id=principal.id,
        payload={"task": task_payload(task)},
    )
    _, message_event = await create_evented_message(
        session,
        group_id=task.group_id,
        actor_agent_id=principal.id,
        flow_type=FlowType.START.value,
        message_type=MessageType.PROPOSAL.value,
        content={
            "text": f"Collaboration object created: {task.title}",
            "payload": {"collaboration_ref": str(task.id), "title": task.title},
            "source": "group_collaboration_create",
        },
    )
    await session.commit()
    await session.refresh(task)
    await publish_event(task_event)
    await publish_event(message_event)
    return task


async def claim_task(
    session: AsyncSession,
    task_id: uuid.UUID,
    actor: Any,
    payload: TaskClaimRequest,
) -> Task:
    principal = _principal_agent(actor)
    task = await get_task_or_404(session, task_id)
    group = await get_group_or_404(session, task.group_id)
    await ensure_membership(session, task.group_id, principal.id)
    ensure_agent_protocol_ready(actor)
    await _validate_protocol_action(
        action_type="task.claim",
        actor=actor,
        group=group,
        payload={"task_id": str(task.id), "note": payload.note},
    )
    task.claimed_by_agent_id = principal.id
    task.status = TaskStatus.CLAIMED.value
    task_event = await append_event(
        session,
        group_id=task.group_id,
        event_type=EventType.TASK_CLAIMED.value,
        aggregate_type="task",
        aggregate_id=task.id,
        actor_agent_id=principal.id,
        payload={"task": task_payload(task), "note": payload.note},
    )
    _, message_event = await create_evented_message(
        session,
        group_id=task.group_id,
        actor_agent_id=principal.id,
        flow_type=FlowType.RUN.value,
        message_type=MessageType.CLAIM.value,
        content={
            "text": payload.note or "Collaboration object claimed",
            "payload": {"collaboration_ref": str(task.id)},
            "source": "group_collaboration_claim",
        },
    )
    await session.commit()
    await session.refresh(task)
    await publish_event(task_event)
    await publish_event(message_event)
    return task


async def update_task_status(
    session: AsyncSession,
    task_id: uuid.UUID,
    actor: Any,
    payload: TaskStatusUpdateRequest,
) -> Task:
    principal = _principal_agent(actor)
    task = await get_task_or_404(session, task_id)
    group = await get_group_or_404(session, task.group_id)
    await ensure_membership(session, task.group_id, principal.id)
    ensure_agent_protocol_ready(actor)
    await _validate_protocol_action(
        action_type="task.update",
        actor=actor,
        group=group,
        payload={"task_id": str(task.id), "status": payload.status.value, "note": payload.note},
    )
    task.status = payload.status.value
    task_event = await append_event(
        session,
        group_id=task.group_id,
        event_type=EventType.TASK_UPDATED.value,
        aggregate_type="task",
        aggregate_id=task.id,
        actor_agent_id=principal.id,
        payload={"task": task_payload(task), "note": payload.note, "status": payload.status.value},
    )
    _, message_event = await create_evented_message(
        session,
        group_id=task.group_id,
        actor_agent_id=principal.id,
        flow_type=FlowType.RUN.value,
        message_type=MessageType.PROGRESS.value,
        content={
            "text": payload.note or payload.status.value,
            "payload": {"collaboration_ref": str(task.id), "collaboration_status": payload.status.value},
            "source": "group_collaboration_status",
        },
    )
    await session.commit()
    await session.refresh(task)
    await publish_event(task_event)
    await publish_event(message_event)
    return task


async def handoff_task(
    session: AsyncSession,
    task_id: uuid.UUID,
    actor: Any,
    payload: TaskHandoffRequest,
) -> Task:
    principal = _principal_agent(actor)
    task = await get_task_or_404(session, task_id)
    group = await get_group_or_404(session, task.group_id)
    await ensure_membership(session, task.group_id, principal.id)
    ensure_agent_protocol_ready(actor)
    await _validate_protocol_action(
        action_type="task.handoff",
        actor=actor,
        group=group,
        payload={
            "task_id": str(task.id),
            "target_agent_id": str(payload.target_agent_id) if payload.target_agent_id else None,
            "summary": payload.summary,
        },
    )
    task.claimed_by_agent_id = payload.target_agent_id
    task.status = TaskStatus.BLOCKED.value if payload.target_agent_id is None else TaskStatus.CLAIMED.value
    task_event = await append_event(
        session,
        group_id=task.group_id,
        event_type=EventType.TASK_HANDOFF.value,
        aggregate_type="task",
        aggregate_id=task.id,
        actor_agent_id=principal.id,
        payload={"task": task_payload(task), "summary": payload.summary},
    )
    _, message_event = await create_evented_message(
        session,
        group_id=task.group_id,
        actor_agent_id=principal.id,
        flow_type=FlowType.RUN.value,
        message_type=MessageType.HANDOFF.value,
        content={
            "text": "Collaboration object handoff",
            "payload": {
                "collaboration_ref": str(task.id),
                "target_agent_id": str(payload.target_agent_id) if payload.target_agent_id else None,
                "summary": payload.summary,
            },
            "source": "group_collaboration_handoff",
        },
    )
    await session.commit()
    await session.refresh(task)
    await publish_event(task_event)
    await publish_event(message_event)
    return task


async def save_task_result(
    session: AsyncSession,
    task_id: uuid.UUID,
    actor: Any,
    payload: TaskResultSummaryRequest,
) -> Task:
    principal = _principal_agent(actor)
    task = await get_task_or_404(session, task_id)
    group = await get_group_or_404(session, task.group_id)
    await ensure_membership(session, task.group_id, principal.id)
    ensure_agent_protocol_ready(actor)
    await _validate_protocol_action(
        action_type="task.result_summary",
        actor=actor,
        group=group,
        payload={"task_id": str(task.id), "summary": payload.summary},
    )
    task.result_summary = payload.summary
    task_event = await append_event(
        session,
        group_id=task.group_id,
        event_type=EventType.TASK_UPDATED.value,
        aggregate_type="task",
        aggregate_id=task.id,
        actor_agent_id=principal.id,
        payload={"task": task_payload(task), "result_summary": payload.summary},
    )
    _, message_event = await create_evented_message(
        session,
        group_id=task.group_id,
        actor_agent_id=principal.id,
        flow_type=FlowType.RESULT.value,
        message_type=MessageType.SUMMARY.value,
        content={
            "text": "Collaboration object result summary",
            "payload": {"collaboration_ref": str(task.id), "summary": payload.summary},
            "source": "group_collaboration_result",
        },
    )
    await session.commit()
    await session.refresh(task)
    await publish_event(task_event)
    await publish_event(message_event)
    return task


async def update_presence(session: AsyncSession, actor: Any, payload: PresenceUpdateRequest) -> Presence:
    principal = _principal_agent(actor)
    await ensure_membership(session, payload.group_id, principal.id)
    presence = await session.scalar(
        select(Presence).where(Presence.group_id == payload.group_id, Presence.agent_id == principal.id)
    )
    if presence is None:
        presence = Presence(group_id=payload.group_id, agent_id=principal.id)
        session.add(presence)

    presence.state = payload.state.value
    presence.note = payload.note
    event = await append_event(
        session,
        group_id=payload.group_id,
        event_type=EventType.PRESENCE_UPDATED.value,
        aggregate_type="presence",
        aggregate_id=presence.id,
        actor_agent_id=principal.id,
        payload={"agent_id": str(principal.id), "state": payload.state.value, "note": payload.note},
    )
    await session.commit()
    await session.refresh(presence)
    await publish_event(event)
    return presence


async def ensure_membership(session: AsyncSession, group_id: uuid.UUID, agent_id: uuid.UUID) -> None:
    membership = await session.scalar(
        select(GroupMembership).where(
            GroupMembership.group_id == group_id,
            GroupMembership.agent_id == agent_id,
        )
    )
    if membership is None:
        raise AppError("agent is not a member of this group", code="membership_required", status_code=403)


async def _get_group_message_or_404(
    session: AsyncSession,
    *,
    message_id: uuid.UUID,
    group_id: uuid.UUID,
    missing_code: str,
    missing_label: str,
) -> Message:
    message = await session.get(Message, message_id)
    if message is None:
        raise AppError(f"{missing_label} not found", code=missing_code, status_code=404)
    if message.group_id != group_id:
        raise AppError(
            f"{missing_label} must belong to the current group",
            code=f"{missing_code}_group_mismatch",
            status_code=400,
        )
    return message


async def _resolve_message_relations(
    session: AsyncSession,
    *,
    group_id: uuid.UUID,
    parent_message_id: uuid.UUID | None,
    thread_id: uuid.UUID | None,
) -> tuple[uuid.UUID | None, uuid.UUID | None]:
    resolved_thread_id = thread_id
    if parent_message_id:
        parent = await _get_group_message_or_404(
            session,
            message_id=parent_message_id,
            group_id=group_id,
            missing_code="parent_not_found",
            missing_label="parent message",
        )
        resolved_thread_id = parent.thread_id or parent.id
        return parent.id, resolved_thread_id

    if resolved_thread_id:
        thread_root = await _get_group_message_or_404(
            session,
            message_id=resolved_thread_id,
            group_id=group_id,
            missing_code="thread_not_found",
            missing_label="thread",
        )
        resolved_thread_id = thread_root.thread_id or thread_root.id

    return None, resolved_thread_id


async def _validate_target_agent(
    session: AsyncSession,
    *,
    group_id: uuid.UUID,
    routing: dict[str, Any] | None,
) -> None:
    if not isinstance(routing, dict):
        return
    target = routing.get("target")
    if not isinstance(target, dict):
        return
    raw_agent_id = str(target.get("agent_id") or "").strip()
    if not raw_agent_id:
        return
    try:
        target_agent_id = uuid.UUID(raw_agent_id)
    except ValueError as exc:
        raise AppError("target agent id is invalid", code="target_agent_invalid", status_code=400) from exc

    agent = await session.get(Agent, target_agent_id)
    if agent is None or not agent.is_active:
        raise AppError("target agent not found", code="target_agent_not_found", status_code=404)
    target_membership = await session.scalar(
        select(GroupMembership).where(
            GroupMembership.group_id == group_id,
            GroupMembership.agent_id == target_agent_id,
        )
    )
    if target_membership is None:
        raise AppError(
            "target agent is not a member of this group",
            code="target_agent_not_in_group",
            status_code=400,
        )


async def require_group_access(session: AsyncSession, group_id: uuid.UUID, actor: Any) -> None:
    if getattr(actor, "actor_type", None) == "admin_user":
        return
    principal_agent = getattr(actor, "agent", actor)
    await ensure_membership(session, group_id, principal_agent.id)


async def create_webhook_subscription(
    session: AsyncSession,
    *,
    group_id: uuid.UUID,
    actor: Any,
    payload: WebhookSubscriptionCreate,
) -> WebhookSubscription:
    await require_group_access(session, group_id, actor)
    existing = await session.scalar(
        select(WebhookSubscription).where(
            WebhookSubscription.group_id == group_id,
            WebhookSubscription.target_url == str(payload.target_url),
        )
    )
    if existing:
        existing.secret = payload.secret
        existing.description = payload.description
        existing.is_active = True
        await session.commit()
        await session.refresh(existing)
        return existing

    subscription = WebhookSubscription(
        group_id=group_id,
        target_url=str(payload.target_url),
        secret=payload.secret,
        description=payload.description,
        is_active=True,
    )
    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)
    return subscription


async def get_group_protocol(session: AsyncSession, group_id: uuid.UUID, actor: Any) -> dict[str, Any]:
    group = await get_group_or_404(session, group_id)
    await require_group_access(session, group_id, actor)
    return {
        "group": group_payload(group),
        "protocol": _group_protocol_context(group),
    }


async def get_group_context(session: AsyncSession, group_id: uuid.UUID, actor: Any) -> dict[str, Any]:
    group = await get_group_or_404(session, group_id)
    await require_group_access(session, group_id, actor)
    return group_context(group)


async def get_agent_protocol_context(
    session: AsyncSession,
    *,
    group_id: uuid.UUID,
    actor: Any,
    action_type: str,
    trigger: str | None = None,
    resource_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    group = await get_group_or_404(session, group_id)
    await require_group_access(session, group_id, actor)
    principal = _principal_agent(actor)
    return agent_protocol_context(
        actor=principal,
        group=group,
        action_type=action_type,
        trigger=trigger,
        resource_id=str(resource_id) if resource_id else None,
        metadata=metadata,
    )


async def update_group_protocol(
    session: AsyncSession,
    *,
    group_id: uuid.UUID,
    actor: Any,
    group_protocol: dict[str, Any],
) -> Group:
    if getattr(actor, "actor_type", None) != "admin_user":
        raise AppError("only admin users can update group protocol", code="admin_required", status_code=403)
    group = await get_group_or_404(session, group_id)
    group.metadata_json = update_group_protocol_metadata(
        group.metadata_json,
        group_name=group.name,
        group_slug=group.slug,
        group_protocol=group_protocol,
    )
    await session.commit()
    await session.refresh(group)
    return group


async def create_agent_webhook_subscription(
    session: AsyncSession,
    *,
    actor: Agent,
    payload: WebhookSubscriptionCreate,
) -> AgentWebhookSubscription:
    existing = await session.scalar(
        select(AgentWebhookSubscription).where(AgentWebhookSubscription.agent_id == actor.id)
    )
    if existing:
        existing.target_url = str(payload.target_url)
        existing.secret = payload.secret
        existing.description = payload.description
        existing.is_active = True
        await session.commit()
        await session.refresh(existing)
        return existing

    subscription = AgentWebhookSubscription(
        agent_id=actor.id,
        target_url=str(payload.target_url),
        secret=payload.secret,
        description=payload.description,
        is_active=True,
    )
    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)
    return subscription


async def get_agent_webhook_subscription(
    session: AsyncSession,
    *,
    actor: Agent,
) -> AgentWebhookSubscription | None:
    return await session.scalar(
        select(AgentWebhookSubscription).where(AgentWebhookSubscription.agent_id == actor.id)
    )


async def deactivate_agent_webhook_subscription(
    session: AsyncSession,
    *,
    actor: Agent,
) -> AgentWebhookSubscription:
    subscription = await session.scalar(
        select(AgentWebhookSubscription).where(AgentWebhookSubscription.agent_id == actor.id)
    )
    if subscription is None:
        raise AppError("agent webhook not found", code="agent_webhook_not_found", status_code=404)
    subscription.is_active = False
    await session.commit()
    await session.refresh(subscription)
    return subscription


async def deactivate_webhook_subscription(
    session: AsyncSession,
    *,
    group_id: uuid.UUID,
    webhook_id: uuid.UUID,
    actor: Any,
) -> WebhookSubscription:
    await require_group_access(session, group_id, actor)
    subscription = await session.get(WebhookSubscription, webhook_id)
    if subscription is None or subscription.group_id != group_id:
        raise AppError("webhook not found", code="webhook_not_found", status_code=404)
    subscription.is_active = False
    await session.commit()
    await session.refresh(subscription)
    return subscription


async def get_group_or_404(session: AsyncSession, group_id: uuid.UUID) -> Group:
    group = await session.get(Group, group_id)
    if group is None:
        raise AppError("group not found", code="group_not_found", status_code=404)
    return group


async def get_group_by_slug_or_404(session: AsyncSession, slug: str) -> Group:
    group = await session.scalar(select(Group).where(Group.slug == slug))
    if group is None:
        raise AppError("group not found", code="group_not_found", status_code=404)
    return group


async def get_task_or_404(session: AsyncSession, task_id: uuid.UUID) -> Task:
    task = await session.get(Task, task_id)
    if task is None:
        raise AppError("task not found", code="task_not_found", status_code=404)
    return task


def group_payload(group: Group) -> dict[str, Any]:
    return {
        "id": str(group.id),
        "name": group.name,
        "slug": group.slug,
        "description": group.description,
        "group_type": group.group_type,
        "metadata_json": _effective_group_metadata(group),
    }


def task_payload(task: Task) -> dict[str, Any]:
    return {
        "id": str(task.id),
        "group_id": str(task.group_id),
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "claimed_by_agent_id": str(task.claimed_by_agent_id) if task.claimed_by_agent_id else None,
        "parent_task_id": str(task.parent_task_id) if task.parent_task_id else None,
        "metadata_json": task.metadata_json,
        "result_summary": task.result_summary,
    }


def message_payload(message: Message) -> dict[str, Any]:
    return serialize_message_v2(message)


async def create_evented_message(
    session: AsyncSession,
    *,
    group_id: uuid.UUID,
    actor_agent_id: uuid.UUID,
    parent_message_id: uuid.UUID | None = None,
    thread_id: uuid.UUID | None = None,
    flow_type: str,
    message_type: str,
    content: dict[str, Any] | str,
) -> tuple[Message, Event]:
    raw_content = content if isinstance(content, dict) else {"text": str(content or "")}
    message = Message(
        group_id=group_id,
        agent_id=actor_agent_id,
        author_kind=str(raw_content.get("author_kind") or "").strip() or None,
        parent_message_id=parent_message_id,
        thread_id=thread_id,
        flow_type=flow_type,
        message_type=message_type,
        content={
            "text": raw_content.get("text"),
            "payload": raw_content.get("payload") if isinstance(raw_content.get("payload"), dict) else {},
            "blocks": raw_content.get("blocks") if isinstance(raw_content.get("blocks"), list) else [],
            "attachments": raw_content.get("attachments") if isinstance(raw_content.get("attachments"), list) else [],
        },
        status_block_json=raw_content.get("status_block") if isinstance(raw_content.get("status_block"), dict) else {},
        context_block_json=(
            raw_content.get("context_block") if isinstance(raw_content.get("context_block"), dict) else {}
        ),
        semantics_json={"flow_type": flow_type, "message_type": message_type},
        routing_json={
            "target": {
                "agent_id": raw_content.get("target_agent_id"),
            },
            "mentions": raw_content.get("mentions") if isinstance(raw_content.get("mentions"), list) else [],
        },
        extensions_json={
            "source": raw_content.get("source"),
            "custom": {
                k: v
                for k, v in raw_content.items()
                if k
                not in {
                    "author_kind",
                    "context_block",
                    "status_block",
                    "text",
                    "payload",
                    "blocks",
                    "attachments",
                    "mentions",
                    "source",
                    "target_agent_id",
                }
            },
        },
    )
    session.add(message)
    await session.flush()
    if message.thread_id is None:
        message.thread_id = message.id
        await session.flush()

    event = await append_event(
        session,
        group_id=group_id,
        event_type=EventType.MESSAGE_POSTED.value,
        aggregate_type="message",
        aggregate_id=message.id,
        actor_agent_id=actor_agent_id,
        payload={"message": message_payload(message)},
    )
    return message, event


def paginated(statement: Select[Any], *, limit: int, offset: int) -> Select[Any]:
    return statement.limit(limit).offset(offset)
