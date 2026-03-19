from typing import Any

from app.models.agent import Agent
from app.models.group import Group
from app.services.channel_protocol_binding import (
    COMMUNITY_PROTOCOLS_KEY,
    ensure_channel_protocol_binding,
    read_channel_protocol_binding,
)
from app.services.protocol_context_assembler import (
    PROFILE_RULE_ID,
    PROTOCOL_VERSION,
    build_current_protocol_document,
    build_group_channel_context,
    build_group_protocol_context,
)
from app.services.protocol_context_service import build_agent_protocol_context


def current_protocol_document() -> dict[str, Any]:
    # Facade entrypoint used by API/services. The underlying protocol artifacts stay community-owned.
    return build_current_protocol_document()


def ensure_group_protocol_metadata(metadata: dict[str, Any] | None, *, group_name: str, group_slug: str) -> dict[str, Any]:
    return ensure_channel_protocol_binding(metadata, group_name=group_name, group_slug=group_slug)


def group_protocol_context(group: Group) -> dict[str, Any]:
    return build_group_protocol_context(group)


def group_channel_context(group: Group) -> dict[str, Any]:
    return build_group_channel_context(group)


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


def update_group_channel_protocol_metadata(
    metadata: dict[str, Any] | None,
    *,
    group_name: str,
    group_slug: str,
    channel_protocol: dict[str, Any],
) -> dict[str, Any]:
    effective = ensure_group_protocol_metadata(metadata, group_name=group_name, group_slug=group_slug)
    community_protocols = dict(effective.get(COMMUNITY_PROTOCOLS_KEY) or {})
    current = community_protocols.get("channel") if isinstance(community_protocols.get("channel"), dict) else {}
    merged = dict(current)
    for key, value in (channel_protocol or {}).items():
        merged[key] = value
    community_protocols["channel"] = read_channel_protocol_binding(
        {COMMUNITY_PROTOCOLS_KEY: {"channel": merged}},
        group_name=group_name,
        group_slug=group_slug,
    )
    effective[COMMUNITY_PROTOCOLS_KEY] = community_protocols
    return effective
