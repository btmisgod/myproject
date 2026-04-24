from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent, GroupMembership
from app.models.group import Group
from app.services.channel_protocol_binding import COMMUNITY_PROTOCOLS_KEY
from app.schemas.sync import (
    AgentSessionSyncRequest,
    AgentSessionSyncResponse,
    AgentSessionView,
    GroupContextUpdate,
    GroupSessionDeclaration,
)
from app.services.protocol_manager import PROTOCOL_VERSION, ensure_group_protocol_metadata, group_execution_spec


COMMUNITY_V2_KEY = "community_v2"
DEFAULT_WORKFLOW_ID = "bootstrap-workflow-v1"
DEFAULT_MODE = "bootstrap"
DEFAULT_STAGE = "step0"


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, fallback: str | None = None) -> str:
    text = str(value or "").strip()
    if text:
        return text
    return str(fallback or "")


def _version_token(prefix: str, seed: Any | None = None) -> str:
    if seed is None:
        seed = datetime.now(timezone.utc).isoformat()
    return f"{prefix}:{seed}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_role(value: Any) -> str | None:
    role = str(value or "").strip().lower()
    aliases = {
        "manager": "manager",
        "managers": "manager",
        "worker": "worker",
        "workers": "worker",
        "system": "system",
    }
    return aliases.get(role) or (role or None)


def _string_list(value: Any) -> list[str]:
    result: list[str] = []
    for item in _list(value) if isinstance(value, list) else [value]:
        text = _text(item)
        if text and text not in result:
            result.append(text)
    return result


def _effective_author_role(
    *,
    execution_spec: dict[str, Any],
    observed_author_agent_id: str | None,
    declared_author_role: str | None,
) -> str | None:
    role_directory = _dict(execution_spec.get("role_directory"))
    if observed_author_agent_id:
        if observed_author_agent_id in _string_list(role_directory.get("manager_agent_ids")):
            return "manager"
        if observed_author_agent_id in _string_list(role_directory.get("worker_agent_ids")):
            return "worker"
    # Gate authority must come only from server-trusted role bindings.
    # Client-declared roles remain observable evidence only.
    return None


def _matches_gate_rule(
    observed_entry: dict[str, Any],
    *,
    execution_spec: dict[str, Any],
    current_stage: str,
    gate_rule: dict[str, Any],
    stage_allowed_roles: list[str],
) -> bool:
    workflow_id = _text(execution_spec.get("workflow_id"), DEFAULT_WORKFLOW_ID)
    if _text(observed_entry.get("workflow_id")) != workflow_id:
        return False
    if _text(observed_entry.get("step_id")) != current_stage:
        return False
    allowed_roles = _string_list(gate_rule.get("allowed_roles")) or stage_allowed_roles
    author_role = _normalize_role(observed_entry.get("author_role"))
    if allowed_roles and author_role not in allowed_roles:
        return False
    lifecycle_phase = _text(gate_rule.get("lifecycle_phase"))
    if lifecycle_phase and _text(observed_entry.get("lifecycle_phase")) != lifecycle_phase:
        return False
    accepted_statuses = _string_list(gate_rule.get("step_statuses"))
    if accepted_statuses and _text(observed_entry.get("step_status")) not in accepted_statuses:
        return False
    return True


def _evaluate_current_stage(session_fact: dict[str, Any], execution_spec: dict[str, Any]) -> dict[str, Any]:
    stage_order = _string_list(execution_spec.get("stage_order"))
    stages = _dict(execution_spec.get("stages"))
    initial_stage = _text(execution_spec.get("initial_stage"), DEFAULT_STAGE)
    current_stage = _text(session_fact.get("current_stage"), initial_stage)
    if current_stage not in stages:
        current_stage = initial_stage if initial_stage in stages else _text(stage_order[0] if stage_order else DEFAULT_STAGE)
    stage_spec = _dict(stages.get(current_stage))
    stage_allowed_roles = _string_list(stage_spec.get("allowed_roles"))
    observed_statuses = _list(_dict(session_fact.get("state_json")).get("observed_statuses"))
    gate_matches: dict[str, list[dict[str, Any]]] = {}
    for gate_rule in _list(stage_spec.get("accepted_status_blocks")):
        gate_id = _text(_dict(gate_rule).get("gate_id"))
        if not gate_id:
            continue
        gate_matches[gate_id] = [
            observed_entry
            for observed_entry in observed_statuses
            if isinstance(observed_entry, dict)
            and _matches_gate_rule(
                observed_entry,
                execution_spec=execution_spec,
                current_stage=current_stage,
                gate_rule=_dict(gate_rule),
                stage_allowed_roles=stage_allowed_roles,
            )
        ]

    gates: dict[str, Any] = {}
    satisfied_gates: list[str] = []
    completion_condition = _dict(stage_spec.get("completion_condition"))
    for raw_requirement in _list(completion_condition.get("all_of")):
        requirement = _dict(raw_requirement)
        gate_id = _text(requirement.get("gate_id"))
        if not gate_id:
            continue
        matches = gate_matches.get(gate_id, [])
        matched_agent_ids = _string_list([item.get("author_agent_id") for item in matches])
        required_agent_ids = _string_list(requirement.get("required_agent_ids"))
        min_count = requirement.get("min_count")
        min_distinct_agents = requirement.get("min_distinct_agents")
        matched_required = [agent_id for agent_id in required_agent_ids if agent_id in matched_agent_ids]
        gate_ok = len(matches) >= (int(min_count) if isinstance(min_count, int) and min_count > 0 else 1)
        if required_agent_ids:
            gate_ok = gate_ok and len(matched_required) == len(required_agent_ids)
        if isinstance(min_distinct_agents, int) and min_distinct_agents > 0:
            gate_ok = gate_ok and len(matched_agent_ids) >= min_distinct_agents
        gates[gate_id] = {
            "satisfied": gate_ok,
            "matched_count": len(matches),
            "matched_agent_ids": matched_agent_ids,
            "required_agent_ids": required_agent_ids,
            "message_ids": _string_list([item.get("message_id") for item in matches]),
        }
        if gate_ok:
            satisfied_gates.append(gate_id)

    current_stage_complete = bool(gates) and all(_dict(info).get("satisfied") for info in gates.values())
    next_stage = _text(stage_spec.get("next_stage")) or None
    next_required_formal_signal = {}
    if not current_stage_complete:
        accepted_status_blocks = [_dict(item) for item in _list(stage_spec.get("accepted_status_blocks")) if isinstance(item, dict)]
        for raw_requirement in _list(completion_condition.get("all_of")):
            requirement = _dict(raw_requirement)
            gate_id = _text(requirement.get("gate_id"))
            if not gate_id:
                continue
            gate_info = _dict(gates.get(gate_id))
            if gate_info.get("satisfied"):
                continue
            matching_rule = next(
                (
                    rule
                    for rule in accepted_status_blocks
                    if _text(rule.get("gate_id")) == gate_id and _string_list(rule.get("step_statuses"))
                ),
                {},
            )
            if not matching_rule:
                continue
            allowed_roles = _string_list(matching_rule.get("allowed_roles")) or stage_allowed_roles
            next_required_formal_signal = {
                "producer_role": _text(allowed_roles[0] if allowed_roles else "") or None,
                "lifecycle_phase": _text(matching_rule.get("lifecycle_phase")) or None,
                "step_status": _text((_string_list(matching_rule.get("step_statuses")) or [None])[0]) or None,
                "step_id": current_stage,
                "gate_id": gate_id,
                "required_agent_ids": gate_info.get("required_agent_ids") or _string_list(requirement.get("required_agent_ids")),
                "reason": "unsatisfied_current_stage_gate",
            }
            break
    return {
        "current_stage": current_stage,
        "current_stage_complete": current_stage_complete,
        "satisfied_gates": satisfied_gates,
        "next_stage_allowed": bool(current_stage_complete and next_stage),
        "next_stage": next_stage,
        "gates": gates,
        "stage_order": stage_order,
        "next_required_formal_signal": next_required_formal_signal,
    }


def _stage_snapshot_payload(evaluation: dict[str, Any], *, evaluated_at: str) -> dict[str, Any]:
    return {
        "evaluated_at": evaluated_at,
        "current_stage_complete": evaluation["current_stage_complete"],
        "satisfied_gates": evaluation["satisfied_gates"],
        "next_stage_allowed": evaluation["next_stage_allowed"],
        "next_stage": evaluation["next_stage"],
        "gates": evaluation["gates"],
        "next_required_formal_signal": _dict(evaluation.get("next_required_formal_signal")),
    }


def _apply_stage_engine(
    session_fact: dict[str, Any],
    execution_spec: dict[str, Any],
    *,
    version_seed: Any | None = None,
) -> None:
    evaluation = _evaluate_current_stage(session_fact, execution_spec)
    evaluated_at = _now().isoformat()
    gate_snapshot = _dict(session_fact.get("gate_snapshot"))
    stage_snapshots = _dict(gate_snapshot.get("stage_snapshots"))
    stage_snapshots[evaluation["current_stage"]] = _stage_snapshot_payload(evaluation, evaluated_at=evaluated_at)
    top_level_evaluation = evaluation
    top_level_evaluated_at = evaluated_at
    if evaluation["next_stage_allowed"] and evaluation["next_stage"]:
        gate_snapshot["advanced_from"] = evaluation["current_stage"]
        gate_snapshot["advanced_to"] = evaluation["next_stage"]
        gate_snapshot["advanced_at"] = evaluated_at
        session_fact["current_stage"] = evaluation["next_stage"]
        top_level_evaluation = _evaluate_current_stage(session_fact, execution_spec)
        top_level_evaluated_at = _now().isoformat()
        stage_snapshots[top_level_evaluation["current_stage"]] = _stage_snapshot_payload(
            top_level_evaluation,
            evaluated_at=top_level_evaluated_at,
        )
    gate_snapshot.update(
        {
            "execution_spec_id": _text(execution_spec.get("execution_spec_id")),
            "workflow_id": _text(execution_spec.get("workflow_id"), DEFAULT_WORKFLOW_ID),
            "current_stage": top_level_evaluation["current_stage"],
            "current_stage_complete": top_level_evaluation["current_stage_complete"],
            "satisfied_gates": top_level_evaluation["satisfied_gates"],
            "next_stage_allowed": top_level_evaluation["next_stage_allowed"],
            "next_stage": top_level_evaluation["next_stage"],
            "gates": top_level_evaluation["gates"],
            "next_required_formal_signal": _dict(top_level_evaluation.get("next_required_formal_signal")),
            "last_evaluated_at": top_level_evaluated_at,
            "stage_order": top_level_evaluation["stage_order"],
            "stage_snapshots": stage_snapshots,
        }
    )
    session_fact["gate_snapshot"] = gate_snapshot
    session_fact["next_required_formal_signal"] = _dict(top_level_evaluation.get("next_required_formal_signal"))
    session_fact["group_session_version"] = _version_token("group-session", version_seed or top_level_evaluated_at)


def _gate_snapshot_semantic_view(gate_snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "execution_spec_id": _text(gate_snapshot.get("execution_spec_id")),
        "workflow_id": _text(gate_snapshot.get("workflow_id"), DEFAULT_WORKFLOW_ID),
        "current_stage": _text(gate_snapshot.get("current_stage")),
        "current_stage_complete": bool(gate_snapshot.get("current_stage_complete")),
        "satisfied_gates": _string_list(gate_snapshot.get("satisfied_gates")),
        "next_stage_allowed": bool(gate_snapshot.get("next_stage_allowed")),
        "next_stage": _text(gate_snapshot.get("next_stage")) or None,
        "gates": _dict(gate_snapshot.get("gates")),
        "next_required_formal_signal": _dict(gate_snapshot.get("next_required_formal_signal")),
    }


def _expected_gate_snapshot_semantics(session_fact: dict[str, Any], execution_spec: dict[str, Any]) -> dict[str, Any]:
    evaluation = _evaluate_current_stage(session_fact, execution_spec)
    return {
        "execution_spec_id": _text(execution_spec.get("execution_spec_id")),
        "workflow_id": _text(execution_spec.get("workflow_id"), DEFAULT_WORKFLOW_ID),
        "current_stage": evaluation["current_stage"],
        "current_stage_complete": evaluation["current_stage_complete"],
        "satisfied_gates": evaluation["satisfied_gates"],
        "next_stage_allowed": evaluation["next_stage_allowed"],
        "next_stage": evaluation["next_stage"],
        "gates": evaluation["gates"],
        "next_required_formal_signal": _dict(evaluation.get("next_required_formal_signal")),
    }


def _gate_snapshot_needs_refresh(session_fact: dict[str, Any], execution_spec: dict[str, Any]) -> bool:
    gate_snapshot = _dict(session_fact.get("gate_snapshot"))
    if not gate_snapshot:
        return True
    return _gate_snapshot_semantic_view(gate_snapshot) != _expected_gate_snapshot_semantics(session_fact, execution_spec)


def _group_context_seed(group: Group) -> dict[str, Any]:
    metadata = _dict(group.metadata_json)
    return {
        "group_id": str(group.id),
        "group_name": group.name,
        "group_slug": group.slug,
        "group_type": group.group_type,
        "protocol_version": _text(metadata.get("protocol_version"), PROTOCOL_VERSION),
    }


def _replace_group_metadata(group: Group, metadata: dict[str, Any] | None) -> dict[str, Any]:
    replaced = deepcopy(_dict(metadata))
    group.metadata_json = replaced
    return replaced


def _should_reseed_group_session(
    session_fact: dict[str, Any],
    execution_spec: dict[str, Any],
    *,
    initial_stage: str,
) -> bool:
    if not session_fact:
        return False

    expected_workflow_id = _text(execution_spec.get("workflow_id"), DEFAULT_WORKFLOW_ID)
    expected_execution_spec_id = _text(execution_spec.get("execution_spec_id"))
    gate_snapshot = _dict(session_fact.get("gate_snapshot"))
    current_workflow_id = _text(session_fact.get("workflow_id"))
    snapshot_workflow_id = _text(gate_snapshot.get("workflow_id"))
    snapshot_execution_spec_id = _text(gate_snapshot.get("execution_spec_id"))
    current_stage = _text(session_fact.get("current_stage"))
    snapshot_stage = _text(gate_snapshot.get("current_stage"))
    stage_order = [stage for stage in _list(execution_spec.get("stage_order")) if _text(stage)]
    valid_stages = {initial_stage, *stage_order}
    valid_stages.discard("")

    if current_workflow_id and current_workflow_id != expected_workflow_id:
        return True
    if snapshot_workflow_id and snapshot_workflow_id != expected_workflow_id:
        return True
    if expected_execution_spec_id and snapshot_execution_spec_id and snapshot_execution_spec_id != expected_execution_spec_id:
        return True
    if current_stage and valid_stages and current_stage not in valid_stages:
        return True
    if snapshot_stage and valid_stages and snapshot_stage not in valid_stages:
        return True
    return False


def ensure_group_session_fact(group: Group) -> dict[str, Any]:
    metadata = _replace_group_metadata(
        group,
        ensure_group_protocol_metadata(group.metadata_json, group_name=group.name, group_slug=group.slug),
    )
    group_protocol = _dict(_dict(metadata.get(COMMUNITY_PROTOCOLS_KEY)).get("channel"))
    group_session_seed = _dict(group_protocol.get("group_session_seed"))
    seed_gate_snapshot = deepcopy(_dict(group_session_seed.get("gate_snapshot")))
    seed_state_json = deepcopy(_dict(group_session_seed.get("state_json")))
    community = _dict(metadata.get(COMMUNITY_V2_KEY))
    stored_session_fact = _dict(community.get("group_session"))
    group_context = _dict(community.get("group_context"))
    execution_spec = group_execution_spec(group)
    initial_stage = _text(execution_spec.get("initial_stage"), DEFAULT_STAGE)
    reseed_session = _should_reseed_group_session(stored_session_fact, execution_spec, initial_stage=initial_stage)
    session_fact = (
        {
            "group_session_id": _text(stored_session_fact.get("group_session_id"), str(group.id)),
            "workflow_id": _text(group_session_seed.get("workflow_id"), _text(execution_spec.get("workflow_id"), DEFAULT_WORKFLOW_ID)),
            "current_mode": _text(group_session_seed.get("current_mode"), DEFAULT_MODE),
            "current_stage": _text(group_session_seed.get("current_stage"), initial_stage),
            "gate_snapshot": seed_gate_snapshot,
            "state_json": seed_state_json,
        }
        if reseed_session
        else stored_session_fact
    )

    if not group_context:
        group_context = _group_context_seed(group)

    protocol_version = _text(
        session_fact.get("protocol_version") or group_context.get("protocol_version") or metadata.get("protocol_version"),
        PROTOCOL_VERSION,
    )
    group_context_version = _text(community.get("group_context_version"), _version_token("group-context", group.id))
    group_session_version = _text(
        session_fact.get("group_session_version"),
        _version_token("group-session-reset" if reseed_session else "group-session", group.id),
    )
    session_fact = {
        "group_id": str(group.id),
        "group_session_id": _text(session_fact.get("group_session_id"), str(group.id)),
        "group_session_version": group_session_version,
        "protocol_version": protocol_version,
        "workflow_id": _text(
            session_fact.get("workflow_id"),
            _text(group_session_seed.get("workflow_id"), _text(execution_spec.get("workflow_id"), DEFAULT_WORKFLOW_ID)),
        ),
        "current_mode": _text(session_fact.get("current_mode"), _text(group_session_seed.get("current_mode"), DEFAULT_MODE)),
        "current_stage": _text(session_fact.get("current_stage"), _text(group_session_seed.get("current_stage"), initial_stage)),
        "group_context_version": group_context_version,
        "gate_snapshot": _dict(session_fact.get("gate_snapshot")) or deepcopy(seed_gate_snapshot),
        "state_json": _dict(session_fact.get("state_json")) or deepcopy(seed_state_json),
    }
    if _gate_snapshot_needs_refresh(session_fact, execution_spec):
        _apply_stage_engine(session_fact, execution_spec, version_seed=_now().isoformat())

    community["group_context"] = group_context
    community["group_context_version"] = group_context_version
    community["group_session"] = session_fact
    metadata[COMMUNITY_V2_KEY] = community
    _replace_group_metadata(group, metadata)
    return session_fact


def update_group_session_from_message(
    group: Group,
    canonical_message: dict[str, Any],
    *,
    message_id: Any | None = None,
    actor_agent_id: Any | None = None,
) -> dict[str, Any]:
    session_fact = ensure_group_session_fact(group)
    metadata = _dict(group.metadata_json)
    community = _dict(metadata.get(COMMUNITY_V2_KEY))
    group_context = _dict(community.get("group_context"))
    status_block = _dict(canonical_message.get("status_block"))
    context_block = _dict(canonical_message.get("context_block"))
    execution_spec = group_execution_spec(group)
    changed = False

    if status_block:
        state_json = _dict(session_fact.get("state_json"))
        observed_statuses = state_json.get("observed_statuses")
        if not isinstance(observed_statuses, list):
            observed_statuses = []
        declared_author_role = _normalize_role(status_block.get("author_role"))
        observed_author_agent_id = _text(actor_agent_id) or _text(status_block.get("author_agent_id")) or None
        observed_entry = {
            "message_id": str(message_id) if message_id else None,
            "workflow_id": _text(status_block.get("workflow_id")) or None,
            "step_id": _text(status_block.get("step_id")) or None,
            "lifecycle_phase": _text(status_block.get("lifecycle_phase")) or None,
            "step_status": _text(status_block.get("step_status")) or None,
            "related_message_id": _text(status_block.get("related_message_id")) or None,
            "declared_author_agent_id": _text(status_block.get("author_agent_id")) or None,
            "author_agent_id": observed_author_agent_id,
            "declared_author_role": declared_author_role,
            "author_role": _effective_author_role(
                execution_spec=execution_spec,
                observed_author_agent_id=observed_author_agent_id,
                declared_author_role=declared_author_role,
            ),
            "observed_at": _now().isoformat(),
        }
        session_fact["state_json"] = {
            **state_json,
            "last_status_block": status_block,
            "observed_statuses": [*observed_statuses[-19:], observed_entry],
            "last_message_id": str(message_id) if message_id else None,
        }
        # Server-side gate evaluation remains authoritative. Raw client status
        # blocks become observed facts first; only the generic gate engine may
        # advance current_stage after evaluating the execution_spec.
        _apply_stage_engine(session_fact, execution_spec, version_seed=message_id or _now().isoformat())
        changed = True

    if context_block:
        context_value = context_block.get("group_context")
        if isinstance(context_value, dict):
            group_context = context_value
        else:
            group_context = {**group_context, **context_block}
        community["group_context"] = group_context
        community["group_context_version"] = _version_token("group-context", message_id or _now().isoformat())
        session_fact["group_context_version"] = community["group_context_version"]
        changed = True

    if changed:
        community["group_session"] = session_fact
        metadata[COMMUNITY_V2_KEY] = community
        _replace_group_metadata(group, metadata)
    return session_fact


def build_group_session_declaration(group: Group) -> dict[str, Any]:
    session_fact = ensure_group_session_fact(group)
    next_required_formal_signal = _dict(session_fact.get("next_required_formal_signal"))
    if not next_required_formal_signal:
        next_required_formal_signal = _dict(_dict(session_fact.get("gate_snapshot")).get("next_required_formal_signal"))
    return {
        "group_id": str(group.id),
        "group_session_id": session_fact["group_session_id"],
        "group_session_version": session_fact["group_session_version"],
        "protocol_version": session_fact["protocol_version"],
        "workflow_id": session_fact["workflow_id"],
        "current_mode": session_fact["current_mode"],
        "current_stage": session_fact["current_stage"],
        "group_context_version": session_fact["group_context_version"],
        "gate_snapshot": _dict(session_fact.get("gate_snapshot")),
        "next_required_formal_signal": next_required_formal_signal,
    }


def build_group_session_view(group: Group) -> dict[str, Any]:
    session_fact = ensure_group_session_fact(group)
    return {
        **build_group_session_declaration(group),
        "state_json": _dict(session_fact.get("state_json")),
    }


def group_context_sync_view(group: Group) -> dict[str, Any]:
    ensure_group_session_fact(group)
    metadata = _dict(group.metadata_json)
    community = _dict(metadata.get(COMMUNITY_V2_KEY))
    return {
        "group_id": str(group.id),
        "group_context_version": _text(community.get("group_context_version")),
        "group_context": _dict(community.get("group_context")),
    }


def group_session_event_payload(group: Group) -> dict[str, Any]:
    return {
        "group_session": build_group_session_view(group),
        "group_session_declaration": build_group_session_declaration(group),
        "group_context": group_context_sync_view(group),
    }


async def sync_agent_session(
    session: AsyncSession,
    *,
    agent: Agent,
    payload: AgentSessionSyncRequest,
) -> AgentSessionSyncResponse:
    groups = list(
        (
            await session.scalars(
                select(Group).join(GroupMembership, GroupMembership.group_id == Group.id).where(GroupMembership.agent_id == agent.id)
            )
        ).all()
    )
    current_group_ids = {str(group.id) for group in groups}
    requested_group_versions = payload.group_session_versions or {}
    requested_context_versions = payload.group_context_versions or {}
    known_group_ids = set(requested_group_versions) | set(requested_context_versions)
    removed_groups = sorted(known_group_ids - current_group_ids)

    onboarding_required = bool(
        payload.community_protocol_version and payload.community_protocol_version != PROTOCOL_VERSION
    )
    force_full_sync = bool(payload.full_sync_requested or onboarding_required)

    declarations: list[GroupSessionDeclaration] = []
    context_updates: list[GroupContextUpdate] = []
    for group in groups:
        declaration = build_group_session_declaration(group)
        context_view = group_context_sync_view(group)
        group_key = str(group.id)
        if force_full_sync or requested_group_versions.get(group_key) != declaration["group_session_version"]:
            declarations.append(GroupSessionDeclaration.model_validate(declaration))
        if force_full_sync or requested_context_versions.get(group_key) != context_view["group_context_version"]:
            context_updates.append(GroupContextUpdate.model_validate(context_view))

    metadata = _dict(agent.metadata_json)
    community = _dict(metadata.get(COMMUNITY_V2_KEY))
    session_view = {
        "agent_id": agent.id,
        "agent_session_id": _text(payload.agent_session_id, f"agent-session:{agent.id}"),
        "community_protocol_version": PROTOCOL_VERSION,
        "runtime_version": payload.runtime_version,
        "skill_version": payload.skill_version,
        "onboarding_version": payload.onboarding_version,
        "last_sync_at": _now(),
        "state": "active",
    }
    community["agent_session"] = {
        **session_view,
        "group_session_versions": {str(item.group_id): item.group_session_version for item in declarations},
        "group_context_versions": {str(item.group_id): item.group_context_version for item in context_updates},
        "removed_groups": removed_groups,
        "onboarding_required": onboarding_required,
    }
    metadata[COMMUNITY_V2_KEY] = community
    agent.metadata_json = metadata
    await session.commit()
    await session.refresh(agent)

    return AgentSessionSyncResponse(
        community_protocol_version=PROTOCOL_VERSION,
        onboarding_required=onboarding_required,
        sync_mode="full" if force_full_sync else "incremental",
        agent_session=AgentSessionView.model_validate(session_view),
        group_session_declarations=declarations,
        removed_groups=removed_groups,
        group_context_updates=context_updates,
        pending_broadcasts=[],
    )
