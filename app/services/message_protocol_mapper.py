from __future__ import annotations

from typing import Any


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _json_scalar(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(value)


def _normalize_flow_type(value: Any, fallback: str | None = None) -> str:
    flow_type = _text(value) or _text(fallback) or "run"
    if flow_type == "status":
        return _text(fallback) or "run"
    if flow_type not in {"start", "run", "result"}:
        return _text(fallback) or "run"
    return flow_type


def _normalize_author_kind(value: Any, fallback: str | None = None) -> str:
    author_kind = _text(value) or _text(fallback) or "agent"
    if author_kind not in {"agent", "system"}:
        return _text(fallback) or "agent"
    return author_kind


def _status_block_from_sources(*sources: Any) -> dict[str, Any]:
    required_keys = ("workflow_id", "step_id", "lifecycle_phase", "author_agent_id", "author_role", "step_status", "related_message_id")
    for source in sources:
        block = _dict(source)
        if block and any(key in block for key in required_keys):
            return block

    candidate = {}
    for source in sources:
        source_dict = _dict(source)
        candidate.update({key: source_dict.get(key) for key in required_keys if source_dict.get(key) is not None})
    return candidate if any(value is not None for value in candidate.values()) else {}


def _context_block_from_sources(*sources: Any) -> dict[str, Any]:
    for source in sources:
        block = _dict(source)
        if block and any(key in block for key in ("group_context", "context_scope", "context_type", "channel_context", "summary", "text")):
            return block

    candidate = {}
    for source in sources:
        source_dict = _dict(source)
        # group_* is the formal main path. channel_* is retained here only as a
        # deprecated compatibility alias for legacy payload ingestion.
        for key in ("group_context", "context_block", "context_scope", "context_type", "channel_context", "summary", "text"):
            if source_dict.get(key) is not None and candidate.get(key) is None:
                candidate[key] = source_dict.get(key)

    if not candidate:
        return {}
    candidate.setdefault("context_scope", "group")
    candidate.setdefault("context_type", "group_context")
    if candidate.get("group_context") is None:
        candidate["group_context"] = candidate.get("channel_context") or candidate.get("summary") or candidate.get("text")
    return candidate


def _normalize_legacy(payload: dict[str, Any]) -> dict[str, Any]:
    content = _dict(payload.get("content"))
    content_payload = _dict(content.get("payload"))
    metadata = _dict(content.get("metadata"))
    extensions = _dict(payload.get("extensions"))
    custom = _dict(extensions.get("custom"))
    flow_type = _normalize_flow_type(payload.get("flow_type") or metadata.get("flow_type"), "run")
    message_type = _text(payload.get("message_type") or metadata.get("message_type"))
    status_block = _status_block_from_sources(
        payload.get("status_block"),
        content.get("status_block"),
        content_payload.get("status_block"),
        content_payload.get("statusBlock"),
        metadata.get("status_block"),
        metadata,
        custom.get("status_block"),
    )
    context_block = _context_block_from_sources(
        payload.get("context_block"),
        content.get("context_block"),
        content_payload.get("context_block"),
        content_payload.get("contextBlock"),
        metadata.get("context_block"),
        metadata,
        extensions.get("context_block"),
        extensions.get("group_context"),
        extensions.get("channel_context"),
        custom.get("context_block"),
        custom.get("group_context"),
        custom.get("channel_context"),
        payload.get("group_context"),
        payload.get("channel_context"),
        content.get("group_context"),
        content.get("channel_context"),
        content.get("summary"),
        content.get("text"),
    )
    return {
        "id": _text(payload.get("id")),
        "group_id": _text(payload.get("group_id")),
        "author_kind": _normalize_author_kind(
            payload.get("author_kind") or extensions.get("author_kind") or custom.get("author_kind"),
            "agent",
        ),
        "author": {
            "author_kind": _normalize_author_kind(
                payload.get("author_kind") or extensions.get("author_kind") or custom.get("author_kind"),
                "agent",
            ),
            "agent_id": _text(payload.get("agent_id")),
        },
        "flow_type": flow_type,
        "message_type": message_type,
        "content": {
            "text": _text(content.get("text")),
            "payload": {},
            "blocks": _list(content.get("blocks")),
            "attachments": _list(content.get("attachments")),
        },
        "status_block": status_block,
        "context_block": context_block,
        "relations": {
            "thread_id": _text(payload.get("thread_id")),
            "parent_message_id": _text(payload.get("parent_message_id")),
        },
        "routing": {
            "target": {
                "agent_id": _text(payload.get("target_agent_id") or metadata.get("target_agent_id")),
            },
            "mentions": _list(content.get("mentions") or metadata.get("mentions")),
        },
        "extensions": {
            "source": _text(content.get("source") or metadata.get("source")),
            "custom": custom,
            "legacy_metadata": metadata,
        },
    }


def normalize_message_to_canonical_v2(payload: dict[str, Any] | None) -> dict[str, Any]:
    source = _dict(payload)
    if "group_id" in source and "flow_type" in source and "content" in source:
        content = _dict(source.get("content"))
        content_payload = _dict(content.get("payload"))
        metadata = _dict(content.get("metadata"))
        extensions = _dict(source.get("extensions"))
        custom = _dict(extensions.get("custom"))
        status_block = _status_block_from_sources(
            source.get("status_block"),
            content.get("status_block"),
            content_payload.get("status_block"),
            content_payload.get("statusBlock"),
            metadata.get("status_block"),
            metadata,
            custom.get("status_block"),
        )
        context_block = _context_block_from_sources(
            source.get("context_block"),
            content.get("context_block"),
            content_payload.get("context_block"),
            content_payload.get("contextBlock"),
            metadata.get("context_block"),
            metadata,
            extensions.get("context_block"),
            extensions.get("group_context"),
            extensions.get("channel_context"),
            custom.get("context_block"),
            custom.get("group_context"),
            custom.get("channel_context"),
            source.get("group_context"),
            source.get("channel_context"),
            content.get("group_context"),
            content.get("channel_context"),
            content.get("summary"),
            content.get("text"),
        )
        return {
            "id": _text(source.get("id")),
            "group_id": _text(source.get("group_id")),
            "author_kind": _normalize_author_kind(
                _dict(source.get("author")).get("author_kind")
                or source.get("author_kind")
                or extensions.get("author_kind")
                or custom.get("author_kind"),
                "agent",
            ),
            "author": {
                "author_kind": _normalize_author_kind(
                    _dict(source.get("author")).get("author_kind")
                    or source.get("author_kind")
                    or extensions.get("author_kind")
                    or custom.get("author_kind"),
                    "agent",
                ),
                "agent_id": _text(_dict(source.get("author")).get("agent_id") or source.get("agent_id")),
            },
            "flow_type": _normalize_flow_type(source.get("flow_type"), "run"),
            "message_type": _text(source.get("message_type")),
            "content": {
                "text": _text(content.get("text")),
                "payload": _dict(content.get("payload")),
                "blocks": _list(content.get("blocks")),
                "attachments": _list(content.get("attachments")),
            },
            "status_block": status_block,
            "context_block": context_block,
            "relations": {
                "thread_id": _text(_dict(source.get("relations")).get("thread_id") or source.get("thread_id")),
                "parent_message_id": _text(
                    _dict(source.get("relations")).get("parent_message_id") or source.get("parent_message_id")
                ),
            },
            "routing": {
                "target": {
                    "agent_id": _text(
                        _dict(_dict(source.get("routing")).get("target")).get("agent_id")
                        or source.get("target_agent_id")
                    ),
                },
                "mentions": _list(_dict(source.get("routing")).get("mentions")),
            },
            "extensions": _dict(source.get("extensions")),
        }
    return _normalize_legacy(source)


def canonical_v2_to_storage_payload(canonical: dict[str, Any] | None) -> dict[str, Any]:
    source = normalize_message_to_canonical_v2(canonical)
    content = _dict(source.get("content"))
    status_block = _dict(source.get("status_block"))
    context_block = _dict(source.get("context_block"))
    if status_block:
        content.setdefault("status_block", status_block)
    if context_block:
        content.setdefault("context_block", context_block)
    return {
        "content": content,
        "status_block": status_block,
        "context_block": context_block,
        "semantics": {
            "flow_type": source.get("flow_type"),
            "message_type": source.get("message_type"),
        },
        "routing": _dict(source.get("routing")),
        "relations": _dict(source.get("relations")),
        "extensions": _dict(source.get("extensions")),
    }


def serialize_message_v2(message: Any) -> dict[str, Any]:
    content = _dict(getattr(message, "content", {}))
    content_payload = _dict(content.get("payload"))
    semantics = _dict(getattr(message, "semantics_json", {}))
    routing = _dict(getattr(message, "routing_json", {}))
    extensions = _dict(getattr(message, "extensions_json", {}))
    status_block = _dict(
        content.get("status_block")
        or content_payload.get("status_block")
        or content_payload.get("statusBlock")
        or extensions.get("status_block")
    )
    context_block = _dict(
        content.get("context_block")
        or content_payload.get("context_block")
        or content_payload.get("contextBlock")
        or extensions.get("context_block")
    )
    return {
        "id": _json_scalar(getattr(message, "id", None)),
        "group_id": _json_scalar(getattr(message, "group_id", None)),
        "author_kind": _normalize_author_kind(
            extensions.get("author_kind"),
            "system" if getattr(message, "agent_id", None) is None else "agent",
        ),
        "author": {
            "author_kind": _normalize_author_kind(
                extensions.get("author_kind"),
                "system" if getattr(message, "agent_id", None) is None else "agent",
            ),
            "agent_id": _json_scalar(getattr(message, "agent_id", None)),
        },
        "flow_type": _normalize_flow_type(
            getattr(message, "flow_type", None) or semantics.get("flow_type"),
            "run",
        ),
        "message_type": _text(getattr(message, "message_type", None) or semantics.get("message_type")),
        "content": {
            "text": _text(content.get("text")),
            "payload": _dict(content.get("payload")),
            "blocks": _list(content.get("blocks")),
            "attachments": _list(content.get("attachments")),
        },
        "status_block": status_block,
        "context_block": context_block,
        "relations": {
            "thread_id": _json_scalar(getattr(message, "thread_id", None)),
            "parent_message_id": _json_scalar(getattr(message, "parent_message_id", None)),
        },
        "routing": {
            "target": {
                "agent_id": _text(_dict(routing.get("target")).get("agent_id")),
            },
            "mentions": _list(routing.get("mentions")),
        },
        "extensions": extensions,
        "created_at": _json_scalar(getattr(message, "created_at", None)),
        "updated_at": _json_scalar(getattr(message, "updated_at", None)),
    }


def serialize_summary_v2(message: Any | None) -> dict[str, Any]:
    if message is None:
        return {}
    return serialize_message_v2(message)
