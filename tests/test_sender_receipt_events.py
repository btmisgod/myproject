import pytest
from types import SimpleNamespace
from uuid import uuid4

try:
    from app.services.event_bus import _sender_canonicalized_payload, _sender_receipt_payload
    from app.services.protocol_validation_hook import _build_protocol_violation_payload
    from app.services.message_envelope import MessageEnvelope
    from app.services.protocol_validation_types import ProtocolValidationIssue, ProtocolValidationResult
    _IMPORT_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - local dependency guard
    _sender_canonicalized_payload = None
    _sender_receipt_payload = None
    _build_protocol_violation_payload = None
    MessageEnvelope = None
    ProtocolValidationIssue = None
    ProtocolValidationResult = None
    _IMPORT_ERROR = exc


def make_projection(*, debug_echo: bool = False):
    message_id = str(uuid4())
    group_id = str(uuid4())
    return SimpleNamespace(
        group_id=group_id,
        entity={
            "message": {
                "id": message_id,
                "group_id": group_id,
                "author": {"agent_id": str(uuid4())},
                "flow_type": "run",
                "message_type": "analysis",
                "relations": {"thread_id": "thread-001", "parent_message_id": None},
                "content": {"text": "hello from sender", "payload": {}, "blocks": [], "attachments": []},
                "routing": {
                    "target": {"agent_id": None},
                    "mentions": [],
                },
                "extensions": {
                    "client_request_id": "req-123",
                    "outbound_correlation_id": "req-123",
                    "source": "unit-test",
                    "custom": {"debug_outbound_echo": True} if debug_echo else {},
                },
            }
        },
    )


def make_event(group_id: str):
    return {
        "event_id": str(uuid4()),
        "group_id": group_id,
        "actor_agent_id": str(uuid4()),
        "event_type": "message.posted",
        "sequence_id": 42,
        "created_at": None,
    }


def test_sender_receipt_payload_is_minimal_and_non_intake():
    projection = make_projection()
    event = make_event(projection.group_id)

    payload = _sender_receipt_payload(event, projection)

    assert payload is not None
    assert payload["event"]["event_type"] == "message.accepted"
    assert payload["projection_type"] == "sender_receipt"
    assert "message" not in payload["entity"]
    receipt = payload["entity"]["receipt"]
    assert receipt["client_request_id"] == "req-123"
    assert receipt["community_message_id"] == projection.entity["message"]["id"]
    assert receipt["non_intake"] is True
    assert receipt["success"] is True


def test_sender_debug_payload_is_opt_in_and_non_intake():
    projection = make_projection(debug_echo=True)
    event = make_event(projection.group_id)

    payload = _sender_canonicalized_payload(event, projection)

    assert payload is not None
    assert payload["event"]["event_type"] == "outbound.canonicalized"
    assert payload["entity"]["receipt"]["non_intake"] is True
    assert payload["entity"]["receipt"]["debug"] is True
    assert payload["entity"]["canonicalized_message"]["id"] == projection.entity["message"]["id"]


def test_protocol_violation_feedback_becomes_message_rejected_receipt():
    group_id = str(uuid4())
    envelope = MessageEnvelope(
        message_id="msg-001",
        category="channel_message",
        event_type="message.posted",
        channel_id=group_id,
        payload={
            "group_id": group_id,
            "flow_type": "run",
            "message_type": "analysis",
            "content": {
                "text": "bad outbound",
                "payload": {},
                "blocks": [],
                "attachments": [],
            },
            "extensions": {
                "client_request_id": "req-violation",
                "outbound_correlation_id": "req-violation",
            },
        },
        priority="normal",
        timestamp="2026-03-20T00:00:00+00:00",
        source_agent=str(uuid4()),
        thread_id="thread-002",
    )
    result = ProtocolValidationResult(
        action_type="message.post",
        decision="block",
        reason="missing explicit target",
        suggestion="add explicit target",
        issues=[
            ProtocolValidationIssue(
                issue_type="protocol_violation",
                code="missing_target",
                message="missing explicit target",
                decision="block",
                details={"rule": "explicit_target_rule"},
            )
        ],
    )

    payload = _build_protocol_violation_payload(envelope, result)

    assert payload["event"]["event_type"] == "message.rejected"
    receipt = payload["entity"]["receipt"]
    assert receipt["client_request_id"] == "req-violation"
    assert receipt["success"] is False
    assert receipt["status"] == "rejected"
    assert receipt["validator_result"]["decision"] == "block"
    assert receipt["non_intake"] is True


pytestmark = pytest.mark.skipif(_IMPORT_ERROR is not None, reason=f"missing dependency: {_IMPORT_ERROR}")
