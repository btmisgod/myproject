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


def _normalize_legacy(payload: dict[str, Any]) -> dict[str, Any]:
    content = _dict(payload.get("content"))
    metadata = _dict(content.get("metadata"))
    flow_type = _text(payload.get("flow_type") or metadata.get("flow_type")) or "run"
    message_type = _text(payload.get("message_type") or metadata.get("message_type"))
    return {
        "id": _text(payload.get("id")),
        "group_id": _text(payload.get("group_id")),
        "author": {
            "agent_id": _text(payload.get("agent_id")),
        },
        "author_kind": _text(payload.get("author_kind")),
        "flow_type": flow_type,
        "message_type": message_type,
        "content": {
            "text": _text(content.get("text")),
            "payload": {},
            "blocks": _list(content.get("blocks")),
            "attachments": _list(content.get("attachments")),
        },
        "status_block": _dict(payload.get("status_block")),
        "context_block": _dict(payload.get("context_block")),
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
            "legacy_metadata": metadata,
        },
    }


def normalize_message_to_canonical_v2(payload: dict[str, Any] | None) -> dict[str, Any]:
    source = _dict(payload)
    if "group_id" in source and "flow_type" in source and "content" in source:
        return {
            "id": _text(source.get("id")),
            "group_id": _text(source.get("group_id")),
            "author": {
                "agent_id": _text(_dict(source.get("author")).get("agent_id") or source.get("agent_id")),
            },
            "author_kind": _text(source.get("author_kind")),
            "flow_type": _text(source.get("flow_type")) or "run",
            "message_type": _text(source.get("message_type")),
            "content": {
                "text": _text(_dict(source.get("content")).get("text")),
                "payload": _dict(_dict(source.get("content")).get("payload")),
                "blocks": _list(_dict(source.get("content")).get("blocks")),
                "attachments": _list(_dict(source.get("content")).get("attachments")),
            },
            "status_block": _dict(source.get("status_block")),
            "context_block": _dict(source.get("context_block")),
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
    return {
        "content": _dict(source.get("content")),
        "author_kind": _text(source.get("author_kind")),
        "status_block": _dict(source.get("status_block")),
        "context_block": _dict(source.get("context_block")),
        "semantics": {
            "flow_type": source.get("flow_type"),
            "message_type": source.get("message_type"),
        },
        "routing": _dict(source.get("routing")),
        "extensions": _dict(source.get("extensions")),
    }


def serialize_message_v2(message: Any) -> dict[str, Any]:
    content = _dict(getattr(message, "content", {}))
    semantics = _dict(getattr(message, "semantics_json", {}))
    routing = _dict(getattr(message, "routing_json", {}))
    extensions = _dict(getattr(message, "extensions_json", {}))
    return {
        "id": _json_scalar(getattr(message, "id", None)),
        "group_id": _json_scalar(getattr(message, "group_id", None)),
        "author": {
            "agent_id": _json_scalar(getattr(message, "agent_id", None)),
        },
        "author_kind": _text(getattr(message, "author_kind", None)),
        "flow_type": _text(getattr(message, "flow_type", None)) or _text(semantics.get("flow_type")) or "run",
        "message_type": _text(getattr(message, "message_type", None) or semantics.get("message_type")),
        "content": {
            "text": _text(content.get("text")),
            "payload": _dict(content.get("payload")),
            "blocks": _list(content.get("blocks")),
            "attachments": _list(content.get("attachments")),
        },
        "status_block": _dict(getattr(message, "status_block_json", {})),
        "context_block": _dict(getattr(message, "context_block_json", {})),
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
