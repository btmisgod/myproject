from __future__ import annotations

from dataclasses import dataclass, field

from app.services.delivery_adapter import DeliveryAdapter
from app.services.message_envelope import DeliveryResult, RoutingPlan


# Event dispatcher executes the routing plan produced by the Community Message Bus.
# It does not own routing policy or protocol interpretation; it only coordinates
# delivery adapters against the chosen targets.


@dataclass
class EventDispatcher:
    adapters: list[DeliveryAdapter] = field(default_factory=list)

    async def dispatch(self, plan: RoutingPlan) -> list[DeliveryResult]:
        if plan.route_type == "system":
            return await self._dispatch_system(plan)
        return await self._dispatch_delivery_targets(plan)

    async def _dispatch_delivery_targets(self, plan: RoutingPlan) -> list[DeliveryResult]:
        results: list[DeliveryResult] = []
        for target in plan.targets:
            for adapter in self.adapters:
                results.append(await adapter.deliver(plan.envelope, target))
        return results

    async def _dispatch_system(self, plan: RoutingPlan) -> list[DeliveryResult]:
        # Placeholder for internal module dispatch. System events stay inside
        # community and do not require agent-facing delivery by default.
        results: list[DeliveryResult] = []
        for target in plan.targets:
            results.append(
                DeliveryResult(
                    target=target,
                    accepted=True,
                    metadata={"dispatch_mode": "system_internal", "implemented": False},
                )
            )
        return results
