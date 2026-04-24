from app.services.protocol_validation_types import ProtocolValidationIssue, ProtocolValidationRequest


# Placeholder rule checks for community-owned protocol validation.
# These functions intentionally avoid complex business rules in this phase.


DIRECTED_COLLABORATION_INTENTS = (
    "assign",
    "handoff",
    "followup",
    "request_action",
    "request_update",
    "approve",
    "authorize",
)

def _normalized_context_value(request: ProtocolValidationRequest, key: str) -> str:
    return str(request.context.get(key) or "").strip()


def _message_metadata(request: ProtocolValidationRequest) -> dict:
    metadata = request.context.get("message_metadata")
    if isinstance(metadata, dict):
        return metadata
    payload = request.payload if isinstance(request.payload, dict) else {}
    payload_metadata = payload.get("metadata")
    if isinstance(payload_metadata, dict):
        return payload_metadata
    return {}


def _mentions(request: ProtocolValidationRequest) -> list:
    mentions = request.context.get("mentions")
    return mentions if isinstance(mentions, list) else []


def _assignees_from_metadata(metadata: dict) -> list:
    assignees = metadata.get("assignees")
    return assignees if isinstance(assignees, list) else []


def _text_of_request(request: ProtocolValidationRequest) -> str:
    payload = request.payload if isinstance(request.payload, dict) else {}
    text = payload.get("text")
    if isinstance(text, str):
        return text
    content = payload.get("content")
    if isinstance(content, dict):
        content_text = content.get("text")
        if isinstance(content_text, str):
            return content_text
    return ""


def _group_directed_section(request: ProtocolValidationRequest) -> dict:
    section = request.context.get("group_directed_collaboration")
    return section if isinstance(section, dict) else {}


def _public_result_exception_section(request: ProtocolValidationRequest) -> dict:
    section = request.context.get("group_public_result_exception")
    return section if isinstance(section, dict) else {}


def _explicit_target_rule_section(request: ProtocolValidationRequest) -> dict:
    section = request.context.get("group_explicit_target_rule")
    return section if isinstance(section, dict) else {}


def _group_slug(request: ProtocolValidationRequest) -> str:
    return _normalized_context_value(request, "group_slug").lower()


def _flow_type(request: ProtocolValidationRequest) -> str:
    return _normalized_context_value(request, "flow_type").lower()


def _message_type(request: ProtocolValidationRequest) -> str:
    return _normalized_context_value(request, "message_type").lower()


def _is_public_result_exception(request: ProtocolValidationRequest) -> bool:
    section = _public_result_exception_section(request)
    if not section:
        return False
    text = _text_of_request(request).lower()
    metadata = _message_metadata(request)
    if metadata.get("final_output") or metadata.get("approved_by_manager"):
        return True

    includes = section.get("includes")
    markers: list[str] = []
    if isinstance(includes, list):
        markers.extend(str(item).lower() for item in includes)
    markers.extend(["final report", "final roundup", "final completed", "最终报告", "最终汇总", "最终稿"])
    return any(marker in text for marker in markers)


def _missing_target_severity(request: ProtocolValidationRequest) -> str:
    explicit_target_rule = _explicit_target_rule_section(request)
    severity = str(
        explicit_target_rule.get("severity")
        or explicit_target_rule.get("missing_target_severity")
        or ""
    ).strip().lower()
    if severity in {"warn", "block"}:
        return severity
    return "warn"


def _matches_group_directed_collaboration(request: ProtocolValidationRequest) -> bool:
    section = _group_directed_section(request)
    if not section:
        return False
    if _is_public_result_exception(request):
        return False

    intent = _normalized_context_value(request, "intent").lower()
    text = _text_of_request(request).lower()
    group_slug = _group_slug(request)

    if group_slug == "lab-dual-agent-news-test":
        if intent in DIRECTED_COLLABORATION_INTENTS or intent in {"report"}:
            return True
        if any(
            marker in text
            for marker in (
                "capability",
                "理解确认",
                "理解任务",
                "收集结果",
                "补充信息",
                "继续收集",
                "继续执行",
                "review",
                "反馈",
                "审阅",
            )
        ):
            return True

    return bool(section.get("explicit_target_rule"))


def check_structural_message_fields(request: ProtocolValidationRequest) -> list[ProtocolValidationIssue]:
    # V0.5 compatibility layer:
    # message_type / flow_type / intent are optional in this phase and should
    # not block or warn when absent. This check only normalizes the entry point
    # for future structural validation.
    return []


def check_group_membership(request: ProtocolValidationRequest) -> list[ProtocolValidationIssue]:
    # Path-validation rule only:
    # missing group id should block bus routing immediately.
    group_id = str(request.context.get("group_id") or request.group_id or "").strip()
    if group_id:
        return []
    return [
        ProtocolValidationIssue(
            issue_type="group_membership",
            code="group_id_missing",
            message="message bus envelope is missing group_id",
            decision="block",
            details={"reason": "missing group_id", "suggestion": "set a valid group_id before publish"},
        )
    ]


def check_message_target(request: ProtocolValidationRequest) -> list[ProtocolValidationIssue]:
    if request.action_type not in {"message.post", "message.reply"}:
        return []
    if _mentions(request):
        return []
    if _normalized_context_value(request, "target_agent_id"):
        return []
    if _normalized_context_value(request, "target_agent"):
        return []
    if _assignees_from_metadata(_message_metadata(request)):
        return []
    if _is_public_result_exception(request):
        return []

    return [
        ProtocolValidationIssue(
            issue_type="message_target",
            code="missing_target",
            message="message does not include an explicit target",
            decision="warn",
            details={
                "reason": "missing target",
                "suggestion": "add target_agent_id, target_agent, assignees, or @mention when collaboration is directed",
            },
        )
    ]


def check_directed_collaboration_rule(request: ProtocolValidationRequest) -> list[ProtocolValidationIssue]:
    # DirectedCollaborationRule:
    # detect candidate directed collaboration messages and warn when they do not
    # contain explicit target signals.
    metadata = _message_metadata(request)
    intent = _normalized_context_value(request, "intent").lower()
    target_agent = str(metadata.get("target_agent") or request.context.get("target_agent") or "").strip()
    target_agent_id = str(metadata.get("target_agent_id") or request.context.get("target_agent_id") or "").strip()
    assignees = _assignees_from_metadata(metadata)
    mentions = _mentions(request)
    directed_category = bool(request.context.get("directed_collaboration")) or _matches_group_directed_collaboration(
        request
    )

    if _is_public_result_exception(request):
        return []

    candidate = (
        intent in DIRECTED_COLLABORATION_INTENTS
        or bool(target_agent)
        or bool(target_agent_id)
        or bool(assignees)
        or directed_category
    )
    if not candidate:
        return []

    has_explicit_target = bool(mentions) or bool(target_agent) or bool(target_agent_id) or bool(assignees)
    if has_explicit_target:
        return []

    return [
        ProtocolValidationIssue(
            issue_type="directed_collaboration",
            code="missing_explicit_target",
            message="directed collaboration message should include an explicit target signal",
            decision=_missing_target_severity(request),
            details={
                "reason": "missing explicit target",
                "protocol_issue": "missing_explicit_target",
                "rule": "DirectedCollaborationRule",
                "suggestion": "add @mention, target_agent, target_agent_id, or assignees",
            },
        )
    ]


def check_cross_group_discussion(request: ProtocolValidationRequest) -> list[ProtocolValidationIssue]:
    # Path-validation rule only:
    # an explicit wrong-group marker triggers reroute suggestion.
    payload = request.payload if isinstance(request.payload, dict) else {}
    markers: list[str] = []
    text = payload.get("text")
    if isinstance(text, str):
        markers.append(text)
    marker = payload.get("marker")
    if isinstance(marker, str):
        markers.append(marker)
    tags = payload.get("tags")
    if isinstance(tags, list):
        markers.extend(str(item) for item in tags)
    if any(marker in item.lower() for item in markers for marker in ("wrong-group", "wrong-channel")):
        return [
            ProtocolValidationIssue(
                issue_type="cross_group_discussion",
                code="wrong_group_marker_detected",
                message="message appears to belong to a different group",
                decision="reroute_suggest",
                details={
                    "reason": "wrong-group marker detected",
                    "suggestion": "move this collaboration to the suggested group flow",
                    "suggested_group_id": "suggested-group",
                },
            )
        ]
    return []


def check_basic_rule_violations(request: ProtocolValidationRequest) -> list[ProtocolValidationIssue]:
    # Default pass path: no issues means the bus continues normally.
    return []
