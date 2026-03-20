from __future__ import annotations

from datetime import datetime
from typing import Any


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _is_v2_message(payload: dict[str, Any]) -> bool:
    return any(key in payload for key in ("container", "author", "relations", "body", "semantics", "routing", "extensions"))


def _legacy_content(payload: dict[str, Any]) -> dict[str, Any]:
    return _dict(payload.get("content"))


def _legacy_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    return _dict(_legacy_content(payload).get("metadata"))


def normalize_message_to_canonical_v2(payload: dict[str, Any] | None) -> dict[str, Any]:
    source = _dict(payload)
    if _is_v2_message(source):
        container = _dict(source.get("container"))
        author = _dict(source.get("author"))
        relations = _dict(source.get("relations"))
        body = _dict(source.get("body"))
        semantics = _dict(source.get("semantics"))
        routing = _dict(source.get("routing"))
        target = _dict(routing.get("target"))
        extensions = _dict(source.get("extensions"))
        custom = _dict(extensions.get("custom"))
        return {
            "id": _text(source.get("id")),
            "container": {
                "group_id": _text(container.get("group_id") or source.get("group_id")),
            },
            "author": {
                "agent_id": _text(author.get("agent_id") or source.get("agent_id")),
            },
            "relations": {
                "thread_id": _text(relations.get("thread_id") or source.get("thread_id")),
                "parent_message_id": _text(relations.get("parent_message_id") or source.get("parent_message_id")),
                "task_id": _text(relations.get("task_id") or source.get("task_id")),
            },
            "body": {
                "text": _text(body.get("text")),
                "blocks": _list(body.get("blocks")),
                "attachments": _list(body.get("attachments")),
            },
            "semantics": {
                "kind": _text(semantics.get("kind") or source.get("message_type")),
                "intent": _text(semantics.get("intent")),
                "topic": _text(semantics.get("topic")),
            },
            "routing": {
                "target": {
                    "scope": _text(target.get("scope")),
                    "agent_id": _text(target.get("agent_id")),
                    "agent_label": _text(target.get("agent_label")),
                },
                "mentions": _list(routing.get("mentions")),
                "assignees": _list(routing.get("assignees")),
            },
            "extensions": {
                "client_request_id": _text(extensions.get("client_request_id")),
                "outbound_correlation_id": _text(extensions.get("outbound_correlation_id")),
                "source": _text(extensions.get("source")),
                "custom": custom,
            },
        }

    content = _legacy_content(source)
    metadata = _legacy_metadata(source)
    return {
        "id": _text(source.get("id")),
        "container": {
            "group_id": _text(source.get("group_id")),
        },
        "author": {
            "agent_id": _text(source.get("agent_id")),
        },
        "relations": {
            "thread_id": _text(source.get("thread_id")),
            "parent_message_id": _text(source.get("parent_message_id")),
            "task_id": _text(source.get("task_id") or metadata.get("task_id")),
        },
        "body": {
            "text": _text(content.get("text")),
            "blocks": _list(content.get("blocks")),
            "attachments": _list(content.get("attachments")),
        },
        "semantics": {
            "kind": _text(source.get("message_type") or metadata.get("message_type")),
            "intent": _text(content.get("intent") or metadata.get("intent")),
            "topic": _text(metadata.get("topic")),
        },
        "routing": {
            "target": {
                "scope": "agent" if _text(metadata.get("target_agent_id") or metadata.get("target_agent")) else None,
                "agent_id": _text(metadata.get("target_agent_id") or source.get("target_agent_id")),
                "agent_label": _text(metadata.get("target_agent") or source.get("target_agent")),
            },
            "mentions": _list(content.get("mentions") or metadata.get("mentions")),
            "assignees": _list(source.get("assignees") or metadata.get("assignees") or metadata.get("assignment") or metadata.get("targets")),
        },
        "extensions": {
            "client_request_id": _text(metadata.get("client_request_id")),
            "outbound_correlation_id": _text(metadata.get("outbound_correlation_id") or metadata.get("idempotency_key")),
            "source": _text(content.get("source") or metadata.get("source")),
            "custom": {k: v for k, v in metadata.items() if k not in {
                "target_agent_id",
                "target_agent",
                "assignees",
                "assignment",
                "targets",
                "intent",
                "flow_type",
                "message_type",
                "client_request_id",
                "outbound_correlation_id",
                "idempotency_key",
                "source",
                "mentions",
                "task_id",
            }},
        },
    }


def canonical_v2_to_storage_content(canonical: dict[str, Any] | None) -> dict[str, Any]:
    source = normalize_message_to_canonical_v2(canonical)
    return {
        "body": _dict(source.get("body")),
        "semantics": _dict(source.get("semantics")),
        "routing": _dict(source.get("routing")),
        "extensions": _dict(source.get("extensions")),
    }


def _canonical_from_message_model(message: Any) -> dict[str, Any]:
    content = _dict(getattr(message, "content", {}))
    if any(key in content for key in ("body", "semantics", "routing", "extensions")):
        return normalize_message_to_canonical_v2(
            {
                "id": getattr(message, "id", None),
                "container": {"group_id": getattr(message, "group_id", None)},
                "author": {"agent_id": getattr(message, "agent_id", None)},
                "relations": {
                    "thread_id": getattr(message, "thread_id", None),
                    "parent_message_id": getattr(message, "parent_message_id", None),
                    "task_id": getattr(message, "task_id", None),
                },
                "body": _dict(content.get("body")),
                "semantics": {
                    **_dict(content.get("semantics")),
                    "kind": _text(_dict(content.get("semantics")).get("kind") or getattr(message, "message_type", None)),
                },
                "routing": _dict(content.get("routing")),
                "extensions": _dict(content.get("extensions")),
            }
        )
    return normalize_message_to_canonical_v2(
        {
            "id": getattr(message, "id", None),
            "group_id": getattr(message, "group_id", None),
            "agent_id": getattr(message, "agent_id", None),
            "task_id": getattr(message, "task_id", None),
            "parent_message_id": getattr(message, "parent_message_id", None),
            "thread_id": getattr(message, "thread_id", None),
            "message_type": getattr(message, "message_type", None),
            "content": content,
        }
    )


def serialize_message_v2(message: Any) -> dict[str, Any]:
    canonical = _canonical_from_message_model(message)
    return {
        **canonical,
        "created_at": getattr(message, "created_at", None),
        "updated_at": getattr(message, "updated_at", None),
    }


def serialize_summary_v2(message: Any | None) -> dict[str, Any]:
    if message is None:
        return {}
    return serialize_message_v2(message)


def canonical_text(canonical: dict[str, Any] | None) -> str:
    message = normalize_message_to_canonical_v2(canonical)
    return _text(_dict(message.get("body")).get("text")) or ""


def canonical_kind(canonical: dict[str, Any] | None) -> str:
    message = normalize_message_to_canonical_v2(canonical)
    return _text(_dict(message.get("semantics")).get("kind")) or ""


def canonical_v2_to_legacy_message(canonical: dict[str, Any] | None) -> dict[str, Any]:
    source = normalize_message_to_canonical_v2(canonical)
    body = _dict(source.get("body"))
    semantics = _dict(source.get("semantics"))
    routing = _dict(source.get("routing"))
    target = _dict(routing.get("target"))
    extensions = _dict(source.get("extensions"))
    custom = _dict(extensions.get("custom"))
    metadata: dict[str, Any] = {}
    if semantics.get("intent") is not None:
        metadata["intent"] = semantics.get("intent")
    if semantics.get("topic") is not None:
        metadata["topic"] = semantics.get("topic")
    if target.get("agent_id") is not None:
        metadata["target_agent_id"] = target.get("agent_id")
    if target.get("agent_label") is not None:
        metadata["target_agent"] = target.get("agent_label")
    if routing.get("assignees"):
        metadata["assignees"] = routing.get("assignees")
    if extensions.get("client_request_id") is not None:
        metadata["client_request_id"] = extensions.get("client_request_id")
    if extensions.get("outbound_correlation_id") is not None:
        metadata["outbound_correlation_id"] = extensions.get("outbound_correlation_id")
    if extensions.get("source") is not None:
        metadata["source"] = extensions.get("source")
    metadata.update(custom)
    return {
        "id": source.get("id"),
        "group_id": _dict(source.get("container")).get("group_id"),
        "agent_id": _dict(source.get("author")).get("agent_id"),
        "task_id": _dict(source.get("relations")).get("task_id"),
        "parent_message_id": _dict(source.get("relations")).get("parent_message_id"),
        "thread_id": _dict(source.get("relations")).get("thread_id"),
        "message_type": semantics.get("kind"),
        "content": {
            "text": body.get("text"),
            "blocks": _list(body.get("blocks")),
            "attachments": _list(body.get("attachments")),
            "mentions": _list(routing.get("mentions")),
            "source": extensions.get("source"),
            "metadata": metadata,
        },
    }
