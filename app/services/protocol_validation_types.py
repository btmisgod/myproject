from dataclasses import dataclass, field
from typing import Any


PROTOCOL_VALIDATION_DECISIONS = (
    "pass",
    "warn",
    "block",
    "reroute_suggest",
)


@dataclass(frozen=True)
class ProtocolValidationRequest:
    # Community-side validation input for one agent action.
    # The action is interpreted by community, not by the agent.
    action_type: str
    actor_id: str
    group_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProtocolValidationIssue:
    # Minimal issue shape for protocol validation findings.
    issue_type: str
    code: str
    message: str
    decision: str = "warn"
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProtocolValidationResult:
    # Validation result returned to community services. This skeleton does not
    # implement strong enforcement yet; it only standardizes the contract.
    action_type: str
    decision: str
    reason: str | None = None
    suggestion: str | None = None
    issues: list[ProtocolValidationIssue] = field(default_factory=list)
    suggested_group_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
