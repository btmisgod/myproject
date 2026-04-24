from typing import Any

from app.models.agent import Agent
from app.models.group import Group
from app.services.channel_protocol_binding import (
    COMMUNITY_PROTOCOLS_KEY,
    ensure_channel_protocol_binding,
    read_channel_protocol_binding,
)
from app.services import protocol_context_assembler as _protocol_context_assembler
from app.services.protocol_context_assembler import (
    build_current_protocol_document,
    build_group_context,
    build_group_protocol_context,
)
from app.services.protocol_context_service import build_agent_protocol_context

PROFILE_RULE_ID = _protocol_context_assembler.PROFILE_RULE_ID
PROTOCOL_VERSION = _protocol_context_assembler.PROTOCOL_VERSION


DEFAULT_EXECUTION_SPEC_ID = "community-server-execution-spec-v1"
DEFAULT_EXECUTION_WORKFLOW_ID = "bootstrap-workflow-v1"
DEFAULT_EXECUTION_INITIAL_STAGE = "step1"
DEFAULT_EXECUTION_STAGE_ORDER = ["step1", "step2", "step3", "task_start"]


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, fallback: str | None = None) -> str:
    text = str(value or "").strip()
    if text:
        return text
    return str(fallback or "")


def _merge_dict(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


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


def _normalize_role_list(values: Any) -> list[str]:
    result: list[str] = []
    for item in values if isinstance(values, list) else [values]:
        normalized = _normalize_role(item)
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _normalize_string_list(values: Any) -> list[str]:
    result: list[str] = []
    for item in values if isinstance(values, list) else [values]:
        text = _text(item)
        if text and text not in result:
            result.append(text)
    return result


def _normalize_gate_rule(raw_rule: Any, *, fallback_gate_id: str) -> dict[str, Any]:
    rule = _dict(raw_rule)
    statuses = rule.get("step_statuses")
    if not isinstance(statuses, list):
        statuses = rule.get("step_status")
    return {
        "gate_id": _text(rule.get("gate_id"), fallback_gate_id),
        "lifecycle_phase": _text(rule.get("lifecycle_phase")) or None,
        "step_statuses": _normalize_string_list(statuses),
        "allowed_roles": _normalize_role_list(rule.get("allowed_roles")),
        "required_agent_ids": _normalize_string_list(rule.get("required_agent_ids")),
    }


def _normalize_completion_condition(raw_condition: Any) -> dict[str, Any]:
    condition = _dict(raw_condition)
    normalized: list[dict[str, Any]] = []
    for index, raw_requirement in enumerate(_list(condition.get("all_of"))):
        requirement = _dict(raw_requirement)
        gate_id = _text(requirement.get("gate_id"))
        if not gate_id:
            gate_id = f"gate-{index + 1}"
        min_count = requirement.get("min_count")
        min_distinct_agents = requirement.get("min_distinct_agents")
        normalized.append(
            {
                "gate_id": gate_id,
                "min_count": int(min_count) if isinstance(min_count, int) and min_count > 0 else 1,
                "min_distinct_agents": (
                    int(min_distinct_agents)
                    if isinstance(min_distinct_agents, int) and min_distinct_agents > 0
                    else 0
                ),
                "required_agent_ids": _normalize_string_list(requirement.get("required_agent_ids")),
            }
        )
    return {"all_of": normalized}


def _normalize_stage_spec(stage_id: str, raw_stage: Any) -> dict[str, Any]:
    stage = _dict(raw_stage)
    accepted_status_blocks = [
        _normalize_gate_rule(raw_rule, fallback_gate_id=f"{stage_id}:gate:{index + 1}")
        for index, raw_rule in enumerate(_list(stage.get("accepted_status_blocks")))
    ]
    return {
        "stage_id": stage_id,
        "semantic_description": _text(stage.get("semantic_description")),
        "allowed_roles": _normalize_role_list(stage.get("allowed_roles")),
        "accepted_status_blocks": accepted_status_blocks,
        "completion_condition": _normalize_completion_condition(stage.get("completion_condition")),
        "next_stage": _text(stage.get("next_stage")) or None,
    }


def _default_execution_spec(protocol: dict[str, Any]) -> dict[str, Any]:
    members = _dict(protocol.get("members"))
    manager_agent_id = _text(members.get("manager_agent_id"))
    worker_agent_ids = _normalize_string_list(members.get("worker_agent_ids"))
    required_worker_count = len(worker_agent_ids) if worker_agent_ids else 1
    return {
        "execution_spec_id": DEFAULT_EXECUTION_SPEC_ID,
        "workflow_id": DEFAULT_EXECUTION_WORKFLOW_ID,
        "initial_stage": DEFAULT_EXECUTION_INITIAL_STAGE,
        "stage_order": list(DEFAULT_EXECUTION_STAGE_ORDER),
        "role_directory": {
            "manager_agent_ids": [manager_agent_id] if manager_agent_id else [],
            "worker_agent_ids": worker_agent_ids,
        },
        "stages": {
            "step1": {
                "stage_id": "step1",
                "semantic_description": "manager aligns the group goal and workers confirm understanding before server advances.",
                "allowed_roles": ["manager", "worker"],
                "accepted_status_blocks": [
                    {
                        "gate_id": "manager_start",
                        "lifecycle_phase": "start",
                        "step_statuses": ["step1_start"],
                        "allowed_roles": ["manager"],
                    },
                    {
                        "gate_id": "worker_run",
                        "lifecycle_phase": "run",
                        "step_statuses": ["step1_submitted"],
                        "allowed_roles": ["worker"],
                    },
                    {
                        "gate_id": "manager_result",
                        "lifecycle_phase": "result",
                        "step_statuses": ["step1_result_aligned", "step1_result_correction_required"],
                        "allowed_roles": ["manager"],
                    },
                    {
                        "gate_id": "manager_done",
                        "lifecycle_phase": "done",
                        "step_statuses": ["step1_done"],
                        "allowed_roles": ["manager"],
                    },
                ],
                "completion_condition": {
                    "all_of": [
                        {
                            "gate_id": "worker_run",
                            "required_agent_ids": worker_agent_ids,
                            "min_distinct_agents": required_worker_count,
                        },
                        {"gate_id": "manager_done", "min_count": 1},
                    ]
                },
                "next_stage": "step2",
            },
            "step2": {
                "stage_id": "step2",
                "semantic_description": "workers confirm capability/scope and manager explicitly closes the stage.",
                "allowed_roles": ["manager", "worker"],
                "accepted_status_blocks": [
                    {
                        "gate_id": "manager_start",
                        "lifecycle_phase": "start",
                        "step_statuses": ["step2_start"],
                        "allowed_roles": ["manager"],
                    },
                    {
                        "gate_id": "worker_run",
                        "lifecycle_phase": "run",
                        "step_statuses": ["step2_submitted", "step2_adjusted"],
                        "allowed_roles": ["worker"],
                    },
                    {
                        "gate_id": "manager_result",
                        "lifecycle_phase": "result",
                        "step_statuses": ["step2_result"],
                        "allowed_roles": ["manager"],
                    },
                    {
                        "gate_id": "manager_done",
                        "lifecycle_phase": "done",
                        "step_statuses": ["step2_done"],
                        "allowed_roles": ["manager"],
                    },
                ],
                "completion_condition": {
                    "all_of": [
                        {
                            "gate_id": "worker_run",
                            "required_agent_ids": worker_agent_ids,
                            "min_distinct_agents": required_worker_count,
                        },
                        {"gate_id": "manager_done", "min_count": 1},
                    ]
                },
                "next_stage": "step3",
            },
            "step3": {
                "stage_id": "step3",
                "semantic_description": "workers confirm ready/install state and manager explicitly opens formal task start.",
                "allowed_roles": ["manager", "worker"],
                "accepted_status_blocks": [
                    {
                        "gate_id": "manager_start",
                        "lifecycle_phase": "start",
                        "step_statuses": ["step3_start"],
                        "allowed_roles": ["manager"],
                    },
                    {
                        "gate_id": "worker_run",
                        "lifecycle_phase": "run",
                        "step_statuses": ["task_ready"],
                        "allowed_roles": ["worker"],
                    },
                    {
                        "gate_id": "manager_result",
                        "lifecycle_phase": "result",
                        "step_statuses": ["step3_result"],
                        "allowed_roles": ["manager"],
                    },
                    {
                        "gate_id": "manager_done",
                        "lifecycle_phase": "done",
                        "step_statuses": ["step3_done"],
                        "allowed_roles": ["manager"],
                    },
                ],
                "completion_condition": {
                    "all_of": [
                        {
                            "gate_id": "worker_run",
                            "required_agent_ids": worker_agent_ids,
                            "min_distinct_agents": required_worker_count,
                        },
                        {"gate_id": "manager_done", "min_count": 1},
                    ]
                },
                "next_stage": "task_start",
            },
            "task_start": {
                "stage_id": "task_start",
                "semantic_description": "manager publishes the formal task start after bootstrap is fully complete.",
                "allowed_roles": ["manager"],
                "accepted_status_blocks": [
                    {
                        "gate_id": "manager_task_start",
                        "lifecycle_phase": "start",
                        "step_statuses": ["task_start"],
                        "allowed_roles": ["manager"],
                    }
                ],
                "completion_condition": {"all_of": [{"gate_id": "manager_task_start", "min_count": 1}]},
                "next_stage": None,
            },
        },
    }


def _ensure_execution_spec(protocol: dict[str, Any]) -> dict[str, Any]:
    default_spec = _default_execution_spec(protocol)
    raw_spec = _dict(protocol.get("execution_spec"))
    merged_spec = _merge_dict(default_spec, raw_spec)
    stage_order = _normalize_string_list(merged_spec.get("stage_order")) or list(DEFAULT_EXECUTION_STAGE_ORDER)
    default_stages = _dict(default_spec.get("stages"))
    merged_stages = _dict(merged_spec.get("stages"))
    stages: dict[str, Any] = {}
    for stage_id in stage_order:
        stage_seed = _merge_dict(_dict(default_stages.get(stage_id)), _dict(merged_stages.get(stage_id)))
        stages[stage_id] = _normalize_stage_spec(stage_id, stage_seed)
    merged = dict(protocol)
    merged["execution_spec"] = {
        "execution_spec_id": _text(merged_spec.get("execution_spec_id"), DEFAULT_EXECUTION_SPEC_ID),
        "workflow_id": _text(merged_spec.get("workflow_id"), DEFAULT_EXECUTION_WORKFLOW_ID),
        "initial_stage": _text(merged_spec.get("initial_stage"), DEFAULT_EXECUTION_INITIAL_STAGE),
        "stage_order": stage_order,
        "role_directory": {
            "manager_agent_ids": _normalize_string_list(_dict(merged_spec.get("role_directory")).get("manager_agent_ids")),
            "worker_agent_ids": _normalize_string_list(_dict(merged_spec.get("role_directory")).get("worker_agent_ids")),
        },
        "stages": stages,
    }
    return merged


def current_protocol_document() -> dict[str, Any]:
    # Facade entrypoint used by API/services. The underlying protocol artifacts stay community-owned.
    return build_current_protocol_document()


def ensure_group_protocol_metadata(metadata: dict[str, Any] | None, *, group_name: str, group_slug: str) -> dict[str, Any]:
    effective = ensure_channel_protocol_binding(metadata, group_name=group_name, group_slug=group_slug)
    community_protocols = dict(effective.get(COMMUNITY_PROTOCOLS_KEY) or {})
    channel = read_channel_protocol_binding(effective, group_name=group_name, group_slug=group_slug)
    community_protocols["channel"] = _ensure_execution_spec(channel)
    effective[COMMUNITY_PROTOCOLS_KEY] = community_protocols
    return effective


def group_protocol_context(group: Group) -> dict[str, Any]:
    return build_group_protocol_context(group)


def group_context(group: Group) -> dict[str, Any]:
    return build_group_context(group)


def agent_protocol_context(
    *,
    actor: Agent,
    group: Group,
    action_type: str,
    trigger: str | None = None,
    resource_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return build_agent_protocol_context(
        actor=actor,
        group=group,
        action_type=action_type,
        trigger=trigger,
        resource_id=resource_id,
        metadata=metadata,
    )


def update_group_protocol_metadata(
    metadata: dict[str, Any] | None,
    *,
    group_name: str,
    group_slug: str,
    group_protocol: dict[str, Any],
) -> dict[str, Any]:
    effective = ensure_group_protocol_metadata(metadata, group_name=group_name, group_slug=group_slug)
    community_protocols = dict(effective.get(COMMUNITY_PROTOCOLS_KEY) or {})
    current = read_channel_protocol_binding(effective, group_name=group_name, group_slug=group_slug)
    merged = dict(current)
    normalized_group_protocol = dict(group_protocol or {})
    layers = normalized_group_protocol.get("layers") if isinstance(normalized_group_protocol.get("layers"), dict) else {}
    if isinstance(layers.get("group"), dict):
        normalized_group_protocol = dict(layers.get("group") or {})
    normalized_group_protocol.pop("layers", None)
    for key, value in normalized_group_protocol.items():
        merged[key] = value
    community_protocols["channel"] = read_channel_protocol_binding(
        {COMMUNITY_PROTOCOLS_KEY: {"channel": merged}},
        group_name=group_name,
        group_slug=group_slug,
    )
    community_protocols["channel"] = _ensure_execution_spec(community_protocols["channel"])
    effective[COMMUNITY_PROTOCOLS_KEY] = community_protocols
    return effective


def group_execution_spec(group: Group) -> dict[str, Any]:
    channel = read_channel_protocol_binding(group.metadata_json, group_name=group.name, group_slug=group.slug)
    return _dict(_ensure_execution_spec(channel).get("execution_spec"))
