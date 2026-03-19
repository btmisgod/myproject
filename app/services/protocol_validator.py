from typing import Any

from app.services.protocol_rule_checks import (
    check_basic_rule_violations,
    check_channel_membership,
    check_cross_channel_discussion,
    check_directed_collaboration_rule,
    check_message_target,
    check_structural_message_fields,
)
from app.services.protocol_validation_types import (
    ProtocolValidationIssue,
    ProtocolValidationRequest,
    ProtocolValidationResult,
)


# Community-side protocol validator facade.
# It centralizes protocol checks for agent behavior so that agents do not
# interpret protocol rules by themselves.


def build_validation_request(
    *,
    action_type: str,
    actor_id: str,
    group_id: str,
    payload: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> ProtocolValidationRequest:
    return ProtocolValidationRequest(
        action_type=action_type,
        actor_id=actor_id,
        group_id=group_id,
        payload=payload or {},
        context=context or {},
    )


def validate_protocol_request(request: ProtocolValidationRequest) -> ProtocolValidationResult:
    issues: list[ProtocolValidationIssue] = []
    issues.extend(check_structural_message_fields(request))
    issues.extend(check_channel_membership(request))
    issues.extend(check_directed_collaboration_rule(request))
    issues.extend(check_message_target(request))
    issues.extend(check_cross_channel_discussion(request))
    issues.extend(check_basic_rule_violations(request))
    decision = "pass"
    reason: str | None = None
    suggestion: str | None = None
    suggested_channel_id: str | None = None
    result_metadata: dict[str, Any] = {"validator": "community.protocol_validator", "phase": "skeleton"}
    if issues:
        priorities = [issue.decision for issue in issues]
        if "block" in priorities:
            decision = "block"
        elif "reroute_suggest" in priorities:
            decision = "reroute_suggest"
        elif "warn" in priorities:
            decision = "warn"
        primary = next((issue for issue in issues if issue.decision == decision), issues[0])
        reason = str(primary.details.get("reason") or primary.message)
        suggestion = primary.details.get("suggestion")
        suggested_channel_id = primary.details.get("suggested_channel_id")
        if primary.details.get("protocol_issue"):
            result_metadata["protocol_issue"] = primary.details.get("protocol_issue")
        if primary.details.get("rule"):
            result_metadata["rule"] = primary.details.get("rule")
    return ProtocolValidationResult(
        action_type=request.action_type,
        decision=decision,
        reason=reason,
        suggestion=suggestion,
        issues=issues,
        suggested_channel_id=suggested_channel_id,
        metadata=result_metadata,
    )
