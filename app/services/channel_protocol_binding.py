from typing import Any

from app.services.protocol_loader import load_channel_protocol_template


COMMUNITY_PROTOCOLS_KEY = "community_protocols"


def _merge_dict(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def build_channel_protocol(*, group_name: str, group_slug: str, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    # Channel protocol remains community-owned. Group metadata only stores the binding payload.
    channel = load_channel_protocol_template()
    channel["name"] = f"{group_name} 频道使用协议"
    channel["channel"] = {"group_name": group_name, "group_slug": group_slug}
    return _merge_dict(channel, existing or {})


def ensure_channel_protocol_binding(
    metadata: dict[str, Any] | None,
    *,
    group_name: str,
    group_slug: str,
) -> dict[str, Any]:
    result = dict(metadata or {})
    community_protocols = result.get(COMMUNITY_PROTOCOLS_KEY) if isinstance(result.get(COMMUNITY_PROTOCOLS_KEY), dict) else {}
    existing_channel = community_protocols.get("channel") if isinstance(community_protocols.get("channel"), dict) else {}
    community_protocols["channel"] = build_channel_protocol(
        group_name=group_name,
        group_slug=group_slug,
        existing=existing_channel,
    )
    result[COMMUNITY_PROTOCOLS_KEY] = community_protocols
    return result


def read_channel_protocol_binding(
    metadata: dict[str, Any] | None,
    *,
    group_name: str,
    group_slug: str,
) -> dict[str, Any]:
    effective = ensure_channel_protocol_binding(metadata, group_name=group_name, group_slug=group_slug)
    community_protocols = effective.get(COMMUNITY_PROTOCOLS_KEY) or {}
    channel = community_protocols.get("channel")
    return channel if isinstance(channel, dict) else build_channel_protocol(group_name=group_name, group_slug=group_slug)
