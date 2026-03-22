from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select

from app.core.exceptions import AppError
from app.db.session import SessionLocal
from app.models.group import Group
from app.models.webhook import AgentWebhookSubscription
from app.services.channel_protocol_binding import read_channel_protocol_binding
from app.services.delivery_adapter import WebhookDeliveryAdapter
from app.services.message_protocol_mapper import normalize_message_to_canonical_v2
from app.services.message_envelope import DeliveryTarget, MessageEnvelope, MessageTarget, envelope_timestamp_now
from app.services.protocol_validation_types import ProtocolValidationResult
from app.services.protocol_validator import build_validation_request, validate_protocol_request


# Community Message Bus pre-route hook for protocol validation.
# This hook performs lightweight group-scoped protocol checks before routing.
# It does not execute complex rule logic in this phase; it only standardizes
# the integration path between Message Bus and the protocol validator.


logger = logging.getLogger(__name__)


def _action_type_from_envelope(envelope: MessageEnvelope) -> str:
    if envelope.category == "channel_message":
        return "message.post"
    if envelope.category == "protocol_reminder":
        return "message.reply"
    if envelope.category == "broadcast_message":
        return "message.post"
    if envelope.category == "system_event":
        return envelope.event_type
    return envelope.event_type


def _context_from_envelope(envelope: MessageEnvelope) -> dict[str, Any]:
    payload = envelope.payload if isinstance(envelope.payload, dict) else {}
    routing = payload.get("routing") if isinstance(payload.get("routing"), dict) else {}
    target = routing.get("target") if isinstance(routing.get("target"), dict) else {}
    payload_metadata = payload.get("metadata")
    message_metadata = payload_metadata if isinstance(payload_metadata, dict) else {}
    payload_mentions = routing.get("mentions") if isinstance(routing.get("mentions"), list) else []
    context_mentions = [
        {
            "mention_type": item.mention_type,
            "mention_id": item.mention_id,
            "display_text": item.display_text,
        }
        for item in envelope.mentions
    ]
    if not context_mentions and payload_mentions:
        context_mentions = [
            item
            for item in payload_mentions
            if isinstance(item, dict)
        ]
    return {
        "category": envelope.category,
        "event_type": envelope.event_type,
        "group_id": envelope.channel_id,
        "channel_id": envelope.channel_id,
        "thread_id": envelope.thread_id,
        "correlation_id": envelope.correlation_id,
        "message_type": payload.get("message_type"),
        "flow_type": payload.get("flow_type"),
        "intent": payload.get("intent") or message_metadata.get("intent"),
        "target_scope": envelope.target.target_scope if envelope.target else None,
        "target_agent_id": (
            envelope.target.target_agent_id if envelope.target and envelope.target.target_agent_id else None
        )
        or target.get("agent_id")
        or message_metadata.get("target_agent_id"),
        "target_agent": target.get("agent_label") or message_metadata.get("target_agent"),
        "assignees": message_metadata.get("assignees"),
        "message_metadata": message_metadata,
        "directed_collaboration": message_metadata.get("directed_collaboration"),
        "mentions": context_mentions,
    }


async def _load_group_protocol_context(group_id: str) -> dict[str, Any]:
    try:
        parsed_group_id = uuid.UUID(str(group_id))
    except Exception:
        return {}

    async with SessionLocal() as session:
        group = (await session.execute(select(Group).where(Group.id == parsed_group_id))).scalar_one_or_none()
        if group is None:
            return {}
        channel_protocol = read_channel_protocol_binding(
            group.metadata_json,
            group_name=group.name,
            group_slug=group.slug,
        )
        sections = channel_protocol.get("sections") if isinstance(channel_protocol.get("sections"), dict) else {}
        directed = sections.get("directed_collaboration") if isinstance(sections.get("directed_collaboration"), dict) else {}
        if not directed:
            communication_rules = (
                sections.get("communication_rules") if isinstance(sections.get("communication_rules"), dict) else {}
            )
            nested_directed = (
                communication_rules.get("directed_collaboration")
                if isinstance(communication_rules.get("directed_collaboration"), dict)
                else {}
            )
            directed = nested_directed
        public_result_exception = (
            directed.get("public_result_exception") if isinstance(directed.get("public_result_exception"), dict) else {}
        )
        explicit_target_rule = (
            directed.get("explicit_target_rule") if isinstance(directed.get("explicit_target_rule"), dict) else {}
        )
        channel = channel_protocol.get("channel") if isinstance(channel_protocol.get("channel"), dict) else {}
        return {
            "group_slug": group.slug,
            "group_type": channel.get("channel_type"),
            "group_directed_collaboration": directed,
            "group_public_result_exception": public_result_exception,
            "group_explicit_target_rule": explicit_target_rule,
        }


async def _load_channel_protocol_context(group_id: str) -> dict[str, Any]:
    # Legacy compatibility alias. Prefer _load_group_protocol_context().
    return await _load_group_protocol_context(group_id)


def _build_protocol_violation_payload(
    envelope: MessageEnvelope,
    result: ProtocolValidationResult,
) -> dict[str, Any]:
    first = result.issues[0] if result.issues else None
    violation_type = first.code if first else "protocol_validation_blocked"
    violation_reason = first.message if first else "protocol validation blocked outbound message"
    violation_details = first.details if first and isinstance(first.details, dict) else {}
    required_fix = (
        violation_details.get("suggestion")
        or result.suggestion
        or "fix the outbound message and resend it"
    )
    canonical_message = normalize_message_to_canonical_v2(envelope.payload if isinstance(envelope.payload, dict) else {})
    extensions = canonical_message.get("extensions") if isinstance(canonical_message.get("extensions"), dict) else {}
    client_request_id = str(
        extensions.get("client_request_id")
        or extensions.get("outbound_correlation_id")
        or (
            extensions.get("custom").get("idempotency_key")
            if isinstance(extensions.get("custom"), dict)
            else None
        )
        or ""
    ).strip() or None
    receipt = {
        "client_request_id": client_request_id,
        "outbound_correlation_id": client_request_id,
        "community_message_id": None,
        "thread_id": envelope.thread_id,
        "status": "rejected",
        "success": False,
        "validator_result": {
            "decision": result.decision,
            "violation_type": violation_type,
            "violation_reason": violation_reason,
            "validator_rule": violation_details.get("rule"),
            "protocol_issue": violation_details.get("protocol_issue"),
            "required_fix": required_fix,
        },
        "projection_result": {
            "projected": False,
            "reason": "validator_blocked",
        },
        "timestamp": envelope.timestamp,
        "non_intake": True,
        "debug": False,
    }
    return {
        "event": {
            "sequence_id": 0,
            "event_id": str(uuid.uuid4()),
            "group_id": envelope.channel_id,
            "event_type": "message.rejected",
            "aggregate_type": "sender_receipt",
            "aggregate_id": envelope.message_id,
            "actor_agent_id": envelope.source_agent,
            "payload": {"receipt": receipt},
            "created_at": envelope.timestamp,
        },
        "entity": {"receipt": receipt},
        "projection_type": "sender_receipt",
        "version": 1,
        "group_id": envelope.channel_id,
    }


async def _resolve_agent_webhook_target(agent_id: str, group_id: str) -> DeliveryTarget | None:
    try:
        parsed_agent_id = uuid.UUID(str(agent_id))
    except Exception:
        return None

    async with SessionLocal() as session:
        subscription = (
            await session.execute(
                select(AgentWebhookSubscription).where(
                    AgentWebhookSubscription.agent_id == parsed_agent_id,
                    AgentWebhookSubscription.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
        if subscription is None:
            return None
        return DeliveryTarget(
            target_type="agent",
            target_id=agent_id,
            group_id=group_id,
            metadata={
                "mode": "sender_receipt",
                "webhook_url": subscription.target_url,
                "webhook_secret": subscription.secret,
            },
        )


async def _deliver_protocol_violation_feedback(
    *,
    envelope: MessageEnvelope,
    result: ProtocolValidationResult,
) -> None:
    if not envelope.source_agent:
        logger.warning(
            "protocol_violation_feedback_skipped",
            extra={
                "reason": "missing_source_agent",
                "channel_id": envelope.channel_id,
                "message_id": envelope.message_id,
            },
        )
        return

    target = await _resolve_agent_webhook_target(envelope.source_agent, envelope.channel_id)
    if target is None:
        logger.warning(
            "protocol_violation_feedback_skipped",
            extra={
                "reason": "agent_webhook_not_found",
                "channel_id": envelope.channel_id,
                "message_id": envelope.message_id,
                "destination_agent": envelope.source_agent,
            },
        )
        return

    payload = _build_protocol_violation_payload(envelope, result)
    feedback_envelope = MessageEnvelope(
        message_id=str(uuid.uuid4()),
        category="system_event",
        event_type="message.rejected",
        channel_id=envelope.channel_id,
        payload={"receipt": payload.get("entity", {}).get("receipt", {})},
        priority="high",
        timestamp=envelope_timestamp_now(),
        source_agent="community_system",
        target=MessageTarget(target_scope="agent", target_agent_id=envelope.source_agent),
        correlation_id=envelope.message_id,
        thread_id=envelope.thread_id,
        metadata={
            "feedback_for_message_id": envelope.message_id,
            "feedback_type": "sender_receipt",
        },
    )
    target.metadata["payload_override"] = payload
    adapter = WebhookDeliveryAdapter(timeout_seconds=5.0)
    result_delivery = await adapter.deliver(feedback_envelope, target)
    issue = result.issues[0] if result.issues else None
    log_payload = {
        "destination_agent": envelope.source_agent,
        "channel_id": envelope.channel_id,
        "original_message_id": envelope.message_id,
        "violation_type": issue.code if issue else "protocol_validation_blocked",
        "accepted": result_delivery.accepted,
        "delivery_metadata": result_delivery.metadata,
    }
    if result_delivery.accepted:
        logger.info("protocol_violation_feedback_delivered", extra=log_payload)
    else:
        logger.warning("protocol_violation_feedback_failed", extra=log_payload)


@dataclass
class ProtocolValidationHook:
    metadata: dict[str, str] = field(
        default_factory=lambda: {"hook": "protocol_validation", "phase": "skeleton", "stage": "pre_route"}
    )

    async def pre_route(self, envelope: MessageEnvelope) -> MessageEnvelope:
        if envelope.category == "system_event":
            return envelope

        result = await self.validate(envelope)
        merged_metadata = dict(envelope.metadata)
        merged_metadata["protocol_validation"] = _result_metadata(result)

        if result.decision == "block":
            first = result.issues[0] if result.issues else None
            logger.warning(
                "protocol_validation_blocked",
                extra={
                    "channel_id": envelope.channel_id,
                    "message_id": envelope.message_id,
                    "source_agent": envelope.source_agent,
                    "violation_type": first.code if first else "protocol_validation_blocked",
                    "validator_rule": (
                        first.details.get("rule")
                        if first and isinstance(first.details, dict)
                        else None
                    ),
                },
            )
            await _deliver_protocol_violation_feedback(envelope=envelope, result=result)
            raise AppError(
                first.message if first else "protocol validation blocked message bus routing",
                code=first.code if first else "protocol_validation_blocked",
                status_code=403,
            )

        if result.decision == "warn":
            merged_metadata["protocol_warning"] = True

        if result.decision == "reroute_suggest":
            merged_metadata["protocol_reroute_suggest"] = True

        return MessageEnvelope(
            message_id=envelope.message_id,
            category=envelope.category,
            event_type=envelope.event_type,
            channel_id=envelope.channel_id,
            payload=envelope.payload,
            priority=envelope.priority,
            timestamp=envelope.timestamp,
            source_agent=envelope.source_agent,
            target=envelope.target,
            mentions=envelope.mentions,
            correlation_id=envelope.correlation_id,
            thread_id=envelope.thread_id,
            metadata=merged_metadata,
        )

    async def pre_delivery(self, plan):
        return plan

    async def post_delivery(self, plan, results) -> None:
        return None

    async def on_error(self, *, stage: str, envelope=None, plan=None, error: Exception, metadata=None) -> None:
        return None

    async def validate(self, envelope: MessageEnvelope) -> ProtocolValidationResult:
        context = _context_from_envelope(envelope)
        context.update(await _load_group_protocol_context(envelope.channel_id))
        request = build_validation_request(
            action_type=_action_type_from_envelope(envelope),
            actor_id=envelope.source_agent or "community_system",
            group_id=envelope.channel_id,
            payload=envelope.payload,
            context=context,
        )
        return validate_protocol_request(request)


def _result_metadata(result: ProtocolValidationResult) -> dict[str, Any]:
    return {
        "decision": result.decision,
        "reason": result.reason,
        "suggestion": result.suggestion,
        "issue_codes": [issue.code for issue in result.issues],
        "suggested_group_id": result.suggested_group_id,
        "metadata": result.metadata,
    }
