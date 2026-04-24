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


def _public_group_protocol_view(protocol: dict[str, Any]) -> dict[str, Any]:
    public = dict(protocol or {})
    channel = public.get("channel") if isinstance(public.get("channel"), dict) else {}
    if channel and not isinstance(public.get("group"), dict):
        public["group"] = dict(channel)
    public.pop("channel", None)
    return public


def _normalize_channel_binding_payload(protocol: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(protocol or {})
    layers = payload.get("layers") if isinstance(payload.get("layers"), dict) else {}
    group_layer = layers.get("group") if isinstance(layers.get("group"), dict) else {}
    if not group_layer:
        return payload
    normalized = {key: value for key, value in payload.items() if key != "layers"}
    normalized = _merge_dict(normalized, dict(group_layer))
    channel = payload.get("channel") if isinstance(payload.get("channel"), dict) else {}
    if channel and not isinstance(normalized.get("channel"), dict):
        normalized["channel"] = dict(channel)
    return normalized


def build_channel_protocol(*, group_name: str, group_slug: str, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    # Channel protocol remains community-owned. Group metadata only stores the binding payload.
    channel = load_channel_protocol_template()
    channel["name"] = f"{group_name} Group Protocol"
    channel["channel"] = {"group_name": group_name, "group_slug": group_slug}
    return _merge_dict(channel, _normalize_channel_binding_payload(existing or {}))


def ensure_channel_protocol_binding(
    metadata: dict[str, Any] | None,
    *,
    group_name: str,
    group_slug: str,
) -> dict[str, Any]:
    result = dict(metadata or {})
    community_protocols = result.get(COMMUNITY_PROTOCOLS_KEY) if isinstance(result.get(COMMUNITY_PROTOCOLS_KEY), dict) else {}
    existing_channel = (
        _normalize_channel_binding_payload(community_protocols.get("channel"))
        if isinstance(community_protocols.get("channel"), dict)
        else {}
    )
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
    return (
        _normalize_channel_binding_payload(channel)
        if isinstance(channel, dict)
        else build_channel_protocol(group_name=group_name, group_slug=group_slug)
    )


def read_group_protocol_binding(
    metadata: dict[str, Any] | None,
    *,
    group_name: str,
    group_slug: str,
) -> dict[str, Any]:
    return _public_group_protocol_view(
        read_channel_protocol_binding(metadata, group_name=group_name, group_slug=group_slug)
    )


def sanitize_group_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    result = dict(metadata or {})
    community_protocols = (
        result.get(COMMUNITY_PROTOCOLS_KEY)
        if isinstance(result.get(COMMUNITY_PROTOCOLS_KEY), dict)
        else None
    )
    if not isinstance(community_protocols, dict):
        return result
    channel = community_protocols.get("channel")
    if isinstance(channel, dict):
        community_protocols["channel"] = _normalize_channel_binding_payload(channel)
    result[COMMUNITY_PROTOCOLS_KEY] = community_protocols
    return result
