import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.schemas.messages import MessageCreate, MessageRead
from app.services.community import message_payload


class MessageProtocolV2SchemaTests(unittest.TestCase):
    def test_message_create_accepts_legacy_input_and_normalizes_to_v2(self) -> None:
        payload = MessageCreate.model_validate(
            {
                "group_id": str(uuid4()),
                "task_id": str(uuid4()),
                "message_type": "analysis",
                "content": {
                    "text": "Legacy payload",
                    "metadata": {
                        "intent": "inform",
                        "target_agent_id": "agent-1",
                        "client_request_id": "req-1",
                    },
                },
            }
        )

        self.assertEqual(payload.body.text, "Legacy payload")
        self.assertEqual(payload.semantics.kind, "analysis")
        self.assertEqual(payload.semantics.intent, "inform")
        self.assertEqual(payload.routing.target.agent_id, "agent-1")
        self.assertEqual(payload.extensions.client_request_id, "req-1")

    def test_message_payload_serializes_model_to_canonical_v2(self) -> None:
        group_id = uuid4()
        agent_id = uuid4()
        task_id = uuid4()
        message = SimpleNamespace(
            id=uuid4(),
            group_id=group_id,
            agent_id=agent_id,
            task_id=task_id,
            parent_message_id=None,
            thread_id=uuid4(),
            message_type="decision",
            content={
                "body": {"text": "Canonical body", "blocks": [], "attachments": []},
                "semantics": {"kind": "decision", "intent": "decide", "topic": None},
                "routing": {
                    "target": {"scope": "agent", "agent_id": "agent-2", "agent_label": "Agent 2"},
                    "mentions": [],
                    "assignees": ["agent-2"],
                },
                "extensions": {
                    "client_request_id": "req-2",
                    "outbound_correlation_id": "corr-2",
                    "source": "unit-test",
                    "custom": {"flag": True},
                },
            },
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        serialized = message_payload(message)

        self.assertEqual(serialized["container"]["group_id"], str(group_id))
        self.assertEqual(serialized["author"]["agent_id"], str(agent_id))
        self.assertEqual(serialized["relations"]["task_id"], str(task_id))
        self.assertEqual(serialized["body"]["text"], "Canonical body")
        self.assertEqual(serialized["semantics"]["kind"], "decision")
        self.assertEqual(serialized["routing"]["target"]["agent_id"], "agent-2")
        self.assertEqual(serialized["extensions"]["client_request_id"], "req-2")

    def test_message_read_model_emits_v2_shape_from_orm_like_model(self) -> None:
        message = SimpleNamespace(
            id=uuid4(),
            group_id=uuid4(),
            agent_id=uuid4(),
            task_id=None,
            parent_message_id=None,
            thread_id=uuid4(),
            message_type="summary",
            content={
                "body": {"text": "Summary note", "blocks": [], "attachments": []},
                "semantics": {"kind": "summary", "intent": "inform", "topic": "recap"},
                "routing": {
                    "target": {"scope": None, "agent_id": None, "agent_label": None},
                    "mentions": [],
                    "assignees": [],
                },
                "extensions": {"client_request_id": None, "outbound_correlation_id": None, "source": "test", "custom": {}},
            },
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        result = MessageRead.model_validate(message).model_dump(mode="json")

        self.assertIn("container", result)
        self.assertIn("body", result)
        self.assertNotIn("message_type", result)
        self.assertEqual(result["semantics"]["kind"], "summary")
        self.assertEqual(result["body"]["text"], "Summary note")


if __name__ == "__main__":
    unittest.main()
