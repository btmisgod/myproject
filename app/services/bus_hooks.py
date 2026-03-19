from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from typing import Protocol

from app.services.message_envelope import DeliveryResult, MessageEnvelope, RoutingPlan


# Message Bus hooks provide stable extension points for protocol validation,
# logging, retry policy, unread tracking, or other cross-cutting behavior.
# Hooks are community-owned and run inside the bus pipeline.


class MessageBusHook(Protocol):
    async def pre_route(self, envelope: MessageEnvelope) -> MessageEnvelope:
        ...

    async def pre_delivery(self, plan: RoutingPlan) -> RoutingPlan:
        ...

    async def post_delivery(self, plan: RoutingPlan, results: list[DeliveryResult]) -> None:
        ...

    async def on_error(
        self,
        *,
        stage: str,
        envelope: MessageEnvelope | None = None,
        plan: RoutingPlan | None = None,
        error: Exception,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        ...


@dataclass
class NoopBusHook:
    metadata: dict[str, str] = field(default_factory=lambda: {"hook": "noop", "phase": "skeleton"})

    async def pre_route(self, envelope: MessageEnvelope) -> MessageEnvelope:
        return envelope

    async def pre_delivery(self, plan: RoutingPlan) -> RoutingPlan:
        return plan

    async def post_delivery(self, plan: RoutingPlan, results: list[DeliveryResult]) -> None:
        return None

    async def on_error(
        self,
        *,
        stage: str,
        envelope: MessageEnvelope | None = None,
        plan: RoutingPlan | None = None,
        error: Exception,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        return None
