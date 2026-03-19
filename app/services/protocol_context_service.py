from typing import Any

from app.models.agent import Agent
from app.models.group import Group
from app.services.channel_protocol_binding import read_channel_protocol_binding
from app.services.protocol_context_assembler import build_current_protocol_document


# Builds the minimal protocol context that community can deliver to an agent
# for a concrete action inside one group/channel. This module intentionally
# does not implement full policy evaluation; it only assembles scoped context.
ACTION_TYPE_ALIASES: dict[str, tuple[str, ...]] = {
    "community.connect": (),
    "channel.enter": (),
    "message.process_unread": ("message.post", "message.reply"),
    "message.catch_up": ("message.post", "message.reply"),
}


def _normalize_action_type(action_type: str) -> str:
    return str(action_type or "").strip().lower()


def _resolved_action_types(action_type: str) -> list[str]:
    normalized = _normalize_action_type(action_type)
    aliases = ACTION_TYPE_ALIASES.get(normalized, ())
    ordered: list[str] = []
    for item in (normalized, *aliases):
        if item and item not in ordered:
            ordered.append(item)
    return ordered


def _scope_applies(scope: list[str] | None, resolved_actions: list[str]) -> bool:
    if not scope:
        return True
    if not resolved_actions:
        return False
    return any(action in scope for action in resolved_actions)


def _layer_rule_refs(layer: dict[str, Any]) -> list[dict[str, Any]]:
    sections = layer.get("sections")
    if not isinstance(sections, dict):
        return []
    outline = sections.get("outline")
    if not isinstance(outline, list):
        return []
    refs: list[dict[str, Any]] = []
    for item in outline:
        if not isinstance(item, dict):
            continue
        refs.append(
            {
                "rule_id": item.get("rule_id") or item.get("id"),
                "title": item.get("title") or item.get("rule_name"),
                "description": item.get("rule_description"),
                "status": item.get("status"),
            }
        )
    return refs


def _minimal_layer_context(layer: dict[str, Any], *, resolved_actions: list[str]) -> dict[str, Any]:
    return {
        "layer_id": layer.get("layer_id"),
        "name": layer.get("name"),
        "summary": layer.get("summary"),
        "precedence_rank": layer.get("precedence_rank"),
        "scope": layer.get("scope", []),
        "scope_applies": _scope_applies(layer.get("scope"), resolved_actions),
        "rule_refs": _layer_rule_refs(layer),
    }


def _applicable_protocol_rules(document: dict[str, Any], resolved_actions: list[str]) -> list[dict[str, Any]]:
    rules = document.get("rules")
    if not isinstance(rules, list):
        return []
    applicable: list[dict[str, Any]] = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        scope = rule.get("scope")
        if isinstance(scope, list) and resolved_actions and not any(action in scope for action in resolved_actions):
            continue
        applicable.append(rule)
    return applicable


def build_agent_protocol_context(
    *,
    actor: Agent,
    group: Group,
    action_type: str,
    trigger: str | None = None,
    resource_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # The returned payload is intentionally scoped for runtime delivery.
    # Community remains the owner of the full protocol documents.
    document = build_current_protocol_document()
    resolved_actions = _resolved_action_types(action_type)
    general_layer = document["layers"]["general"]
    inter_agent_layer = document["layers"]["inter_agent"]
    channel_layer = read_channel_protocol_binding(group.metadata_json, group_name=group.name, group_slug=group.slug)
    applicable_rules = _applicable_protocol_rules(document, resolved_actions)

    return {
        "delivery_mode": "scoped_context",
        "protocol_version": document["version"],
        "protocol_name": document["name"],
        "actor": {
            "agent_id": str(actor.id),
            "agent_name": actor.name,
        },
        "group": {
            "group_id": str(group.id),
            "group_name": group.name,
            "group_slug": group.slug,
        },
        "request": {
            "action_type": _normalize_action_type(action_type),
            "resolved_action_types": resolved_actions,
            "trigger": trigger,
            "resource_id": resource_id,
        },
        "applicable_rule_ids": [rule.get("id") for rule in applicable_rules if isinstance(rule, dict) and rule.get("id")],
        "applicable_rules": applicable_rules,
        "layers": {
            "general": _minimal_layer_context(general_layer, resolved_actions=resolved_actions),
            "inter_agent": _minimal_layer_context(inter_agent_layer, resolved_actions=resolved_actions),
            "channel": _minimal_layer_context(channel_layer, resolved_actions=resolved_actions),
        },
        "channel_protocol_summary": {
            "name": channel_layer.get("name"),
            "summary": channel_layer.get("summary"),
            "channel": channel_layer.get("channel", {}),
        },
        "metadata": metadata or {},
    }
