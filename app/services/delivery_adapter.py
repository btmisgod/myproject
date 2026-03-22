from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

import httpx

from app.services.message_envelope import DeliveryResult, DeliveryTarget, MessageEnvelope
from app.services.message_protocol_mapper import normalize_message_to_canonical_v2


# Delivery adapters are downstream executors for Message Bus routing results.
# They are owned by community and can later target webhook push, internal
# consumers, audit sinks, or other in-process delivery mechanisms.


class DeliveryAdapter(Protocol):
    async def deliver(self, envelope: MessageEnvelope, target: DeliveryTarget) -> DeliveryResult:
        ...


@dataclass
class WebhookDeliveryAdapter:
    default_webhook_url: str | None = None
    default_webhook_secret: str | None = None
    timeout_seconds: float = 5.0
    metadata: dict[str, Any] = field(default_factory=lambda: {"adapter": "webhook", "phase": "skeleton"})

    async def deliver(self, envelope: MessageEnvelope, target: DeliveryTarget) -> DeliveryResult:
        webhook_url = str(target.metadata.get("webhook_url") or self.default_webhook_url or "").strip()
        webhook_secret = str(target.metadata.get("webhook_secret") or self.default_webhook_secret or "").strip()
        if not webhook_url:
            return DeliveryResult(
                target=target,
                accepted=False,
                metadata={"adapter": "webhook", "implemented": True, "error": "missing webhook_url"},
            )

        payload = self._build_payload(envelope, target)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if webhook_secret:
            headers["X-Community-Webhook-Signature"] = hmac.new(
                webhook_secret.encode("utf-8"),
                body,
                hashlib.sha256,
            ).hexdigest()
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(webhook_url, content=body, headers=headers)
        return DeliveryResult(
            target=target,
            accepted=response.is_success,
            metadata={
                "adapter": "webhook",
                "implemented": True,
                "event_type": envelope.event_type,
                "status_code": response.status_code,
                "webhook_url": webhook_url,
            },
        )

    def _build_payload(self, envelope: MessageEnvelope, target: DeliveryTarget) -> dict[str, Any]:
        payload_override = target.metadata.get("payload_override") if isinstance(target.metadata, dict) else None
        if isinstance(payload_override, dict):
            return payload_override

        message_content = dict(envelope.payload)
        message_content.setdefault("metadata", {})
        if not isinstance(message_content["metadata"], dict):
            message_content["metadata"] = {}
        if "mentions" not in message_content and envelope.mentions:
            message_content["mentions"] = [
                {
                    "mention_type": item.mention_type,
                    "mention_id": item.mention_id,
                    "display_text": item.display_text,
                    "metadata": dict(item.metadata),
                }
                for item in envelope.mentions
            ]

        message_metadata: dict[str, Any] = message_content["metadata"]
        if envelope.payload.get("flow_type") is not None and message_content.get("flow_type") is None:
            message_content["flow_type"] = envelope.payload.get("flow_type")
        if message_content.get("flow_type") is not None and message_metadata.get("flow_type") is None:
            message_metadata["flow_type"] = message_content.get("flow_type")
        if message_metadata.get("target_agent_id") is None and envelope.target and envelope.target.target_agent_id:
            message_metadata["target_agent_id"] = envelope.target.target_agent_id
        if message_metadata.get("mentions") is None and message_content.get("mentions") is not None:
            message_metadata["mentions"] = message_content.get("mentions")
        if message_metadata.get("assignees") is None and isinstance(envelope.payload.get("assignees"), list):
            message_metadata["assignees"] = envelope.payload.get("assignees")
        if message_metadata.get("target_agent") is None and envelope.payload.get("target_agent") is not None:
            message_metadata["target_agent"] = envelope.payload.get("target_agent")

        if isinstance(message_content["metadata"], dict):
            message_content["metadata"]["message_bus"] = {
                "category": envelope.category,
                "priority": envelope.priority,
            }
            if envelope.metadata.get("protocol_validation") is not None:
                message_content["metadata"]["protocol_validation"] = envelope.metadata.get("protocol_validation")
            if envelope.metadata.get("protocol_warning") is not None:
                message_content["metadata"]["protocol_warning"] = envelope.metadata.get("protocol_warning")
            if envelope.metadata.get("protocol_reroute_suggest") is not None:
                message_content["metadata"]["protocol_reroute_suggest"] = envelope.metadata.get(
                    "protocol_reroute_suggest"
                )

        message = normalize_message_to_canonical_v2(
            {
                "id": envelope.message_id,
                "group_id": envelope.channel_id,
                "author": {"agent_id": envelope.source_agent},
                "flow_type": envelope.payload.get("flow_type", "run"),
                "message_type": envelope.payload.get("message_type", "analysis"),
                "relations": {
                    "thread_id": envelope.thread_id,
                    "parent_message_id": envelope.payload.get("parent_message_id"),
                },
                "content": {
                    "text": message_content.get("text"),
                    "payload": message_content.get("payload") if isinstance(message_content.get("payload"), dict) else {},
                    "blocks": message_content.get("blocks") if isinstance(message_content.get("blocks"), list) else [],
                    "attachments": (
                        message_content.get("attachments")
                        if isinstance(message_content.get("attachments"), list)
                        else []
                    ),
                },
                "routing": {
                    "target": {
                        "agent_id": message_metadata.get("target_agent_id"),
                    },
                    "mentions": message_content.get("mentions") if isinstance(message_content.get("mentions"), list) else [],
                },
                "extensions": {
                    "client_request_id": message_metadata.get("client_request_id"),
                    "outbound_correlation_id": (
                        message_metadata.get("outbound_correlation_id") or message_metadata.get("idempotency_key")
                    ),
                    "source": message_content.get("source"),
                    "legacy_metadata": message_metadata,
                },
            }
        )
        event = {
            "sequence_id": 0,
            "event_id": envelope.message_id,
            "group_id": envelope.channel_id,
            "event_type": envelope.event_type,
            "aggregate_type": "message",
            "aggregate_id": envelope.message_id,
            "actor_agent_id": envelope.source_agent,
            "payload": {"message": message},
            "created_at": envelope.timestamp,
        }
        return {
            "event": event,
            "entity": {"message": message},
            "projection_type": "group_event",
            "projection": {"type": "group_event", "version": 2},
            "version": 2,
            "group_id": envelope.channel_id,
            "delivery_target": asdict(target),
        }


@dataclass
class InternalConsumerAdapter:
    metadata: dict[str, Any] = field(default_factory=lambda: {"adapter": "internal_consumer", "phase": "skeleton"})

    async def deliver(self, envelope: MessageEnvelope, target: DeliveryTarget) -> DeliveryResult:
        return DeliveryResult(
            target=target,
            accepted=True,
            metadata={"adapter": "internal_consumer", "implemented": False},
        )
