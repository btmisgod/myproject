import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

try:
    from app.schemas.messages import MessageCreate, MessageRead
    from app.services.community import message_payload
    _IMPORT_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - local dependency guard
    MessageCreate = None
    MessageRead = None
    message_payload = None
    _IMPORT_ERROR = exc


@unittest.skipIf(_IMPORT_ERROR is not None, f"missing dependency: {_IMPORT_ERROR}")
class MessageProtocolV2SchemaTests(unittest.TestCase):
    def test_message_create_accepts_legacy_input_and_normalizes_to_v2(self) -> None:
        payload = MessageCreate.model_validate(
            {
                "group_id": str(uuid4()),
                "message_type": "analysis",
                "content": {
                    "text": "Legacy payload",
                    "metadata": {
                        "target_agent_id": "agent-1",
                        "client_request_id": "req-1",
                    },
                },
            }
        )

        self.assertEqual(payload.content.text, "Legacy payload")
        self.assertEqual(payload.flow_type, "run")
        self.assertEqual(payload.message_type, "analysis")
        self.assertEqual(payload.routing.target.agent_id, "agent-1")
        self.assertEqual(payload.extensions["legacy_metadata"]["client_request_id"], "req-1")

    def test_message_payload_serializes_model_to_current_shape(self) -> None:
        group_id = uuid4()
        agent_id = uuid4()
        message = SimpleNamespace(
            id=uuid4(),
            group_id=group_id,
            agent_id=agent_id,
            parent_message_id=None,
            thread_id=uuid4(),
            flow_type="result",
            message_type="decision",
            content={
                "text": "Canonical body",
                "payload": {"decision": "use_postgres"},
                "blocks": [],
                "attachments": [],
            },
            semantics_json={"flow_type": "result", "message_type": "decision"},
            routing_json={
                "target": {"agent_id": "agent-2"},
                "mentions": [],
            },
            extensions_json={
                "client_request_id": "req-2",
                "outbound_correlation_id": "corr-2",
                "source": "unit-test",
            },
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        serialized = message_payload(message)

        self.assertEqual(serialized["group_id"], str(group_id))
        self.assertEqual(serialized["author"]["agent_id"], str(agent_id))
        self.assertEqual(serialized["flow_type"], "result")
        self.assertEqual(serialized["message_type"], "decision")
        self.assertEqual(serialized["content"]["text"], "Canonical body")
        self.assertEqual(serialized["routing"]["target"]["agent_id"], "agent-2")
        self.assertEqual(serialized["extensions"]["client_request_id"], "req-2")

    def test_message_read_model_emits_current_shape_from_orm_like_model(self) -> None:
        message = SimpleNamespace(
            id=uuid4(),
            group_id=uuid4(),
            agent_id=uuid4(),
            parent_message_id=None,
            thread_id=uuid4(),
            flow_type="run",
            message_type="discussion",
            content={
                "text": "Summary note",
                "payload": {},
                "blocks": [],
                "attachments": [],
            },
            semantics_json={"flow_type": "run", "message_type": "discussion"},
            routing_json={"target": {"agent_id": None}, "mentions": []},
            extensions_json={"source": "test"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        result = MessageRead.model_validate(message).model_dump(mode="json")

        self.assertIn("group_id", result)
        self.assertIn("content", result)
        self.assertEqual(result["flow_type"], "run")
        self.assertEqual(result["message_type"], "discussion")
        self.assertEqual(result["content"]["text"], "Summary note")

    def test_message_create_preserves_canonical_routing_and_relations(self) -> None:
        thread_id = uuid4()
        parent_id = uuid4()
        payload = MessageCreate.model_validate(
            {
                "group_id": str(uuid4()),
                "flow_type": "run",
                "message_type": "analysis",
                "content": {"text": "Canonical payload"},
                "relations": {
                    "thread_id": str(thread_id),
                    "parent_message_id": str(parent_id),
                },
                "routing": {
                    "target": {"agent_id": "agent-self"},
                    "mentions": [{"mention_type": "agent", "mention_id": "agent-self"}],
                },
                "extensions": {"source": "unit-test"},
            }
        )

        self.assertEqual(payload.routing.target.agent_id, "agent-self")
        self.assertEqual(str(payload.relations.thread_id), str(thread_id))
        self.assertEqual(str(payload.relations.parent_message_id), str(parent_id))


if __name__ == "__main__":
    unittest.main()
