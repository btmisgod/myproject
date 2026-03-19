from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from app.services.bus_hooks import MessageBusHook, NoopBusHook
from app.services.delivery_adapter import InternalConsumerAdapter, WebhookDeliveryAdapter
from app.services.event_dispatcher import EventDispatcher
from app.services.message_envelope import (
    DeliveryResult,
    MessageEnvelope,
    MessageTarget,
    RoutingPlan,
    envelope_timestamp_now,
)
from app.services.message_router import route_envelope
from app.services.protocol_validation_hook import ProtocolValidationHook


# Community Message Bus public facade.
# Community services should publish messages and events through this entrypoint
# instead of coupling directly to downstream delivery mechanisms.


@dataclass
class MessageBusDispatchReport:
    envelope: MessageEnvelope
    routing_plan: RoutingPlan
    delivery_results: list[DeliveryResult]


@dataclass
class CommunityMessageBus:
    hooks: list[MessageBusHook] = field(default_factory=lambda: [ProtocolValidationHook(), NoopBusHook()])
    dispatcher: EventDispatcher = field(
        default_factory=lambda: EventDispatcher(adapters=[WebhookDeliveryAdapter(), InternalConsumerAdapter()])
    )

    async def publish(self, envelope: MessageEnvelope) -> MessageBusDispatchReport:
        current = envelope
        plan: RoutingPlan | None = None
        try:
            for hook in self.hooks:
                current = await hook.pre_route(current)

            plan = route_envelope(current)
            for hook in self.hooks:
                plan = await hook.pre_delivery(plan)

            results = await self.dispatcher.dispatch(plan)

            for hook in self.hooks:
                await hook.post_delivery(plan, results)

            return MessageBusDispatchReport(envelope=current, routing_plan=plan, delivery_results=results)
        except Exception as exc:
            await self._run_error_hooks(
                stage=self._infer_error_stage(plan),
                envelope=current,
                plan=plan,
                error=exc,
            )
            raise

    async def _run_error_hooks(
        self,
        *,
        stage: str,
        envelope: MessageEnvelope | None,
        plan: RoutingPlan | None,
        error: Exception,
    ) -> None:
        for hook in self.hooks:
            await hook.on_error(
                stage=stage,
                envelope=envelope,
                plan=plan,
                error=error,
                metadata={"bus": "community.message_bus"},
            )

    def _infer_error_stage(self, plan: RoutingPlan | None) -> str:
        if plan is None:
            return "pre_route_or_route"
        return "pre_delivery_or_delivery_or_post_delivery"

    async def publish_event(
        self,
        *,
        group_id: str,
        message_type: str,
        payload: dict[str, Any] | None = None,
        actor_agent_id: str | None = None,
        target_agent_id: str | None = None,
        aggregate_type: str | None = None,
        aggregate_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MessageBusDispatchReport:
        envelope = MessageEnvelope(
            message_id=str(uuid.uuid4()),
            category="system_event",
            event_type=message_type,
            channel_id=group_id,
            source_agent=actor_agent_id,
            target=MessageTarget(target_scope="agent", target_agent_id=target_agent_id) if target_agent_id else None,
            payload=payload or {},
            priority="normal",
            timestamp=envelope_timestamp_now(),
            metadata=metadata or {},
        )
        envelope.metadata.setdefault("aggregate_type", aggregate_type)
        envelope.metadata.setdefault("aggregate_id", aggregate_id)
        return await self.publish(envelope)

    async def publish_message(
        self,
        *,
        group_id: str,
        message_type: str,
        payload: dict[str, Any] | None = None,
        actor_agent_id: str | None = None,
        target_agent_id: str | None = None,
        thread_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MessageBusDispatchReport:
        envelope = MessageEnvelope(
            message_id=str(uuid.uuid4()),
            category="channel_message",
            event_type=message_type,
            channel_id=group_id,
            source_agent=actor_agent_id,
            target=MessageTarget(target_scope="agent", target_agent_id=target_agent_id) if target_agent_id else None,
            thread_id=thread_id,
            payload=payload or {},
            priority="normal",
            timestamp=envelope_timestamp_now(),
            metadata=metadata or {},
        )
        return await self.publish(envelope)


def create_message_bus() -> CommunityMessageBus:
    return CommunityMessageBus()
