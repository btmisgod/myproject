import unittest

from app.services.message_protocol_mapper import normalize_message_to_canonical_v2


class MessageProtocolMapperTests(unittest.TestCase):
    def test_normalize_legacy_message_to_current_shape(self) -> None:
        payload = {
            "group_id": "group-1",
            "thread_id": "thread-1",
            "message_type": "analysis",
            "content": {
                "text": "Need input on this draft.",
                "metadata": {
                    "client_request_id": "req-1",
                },
            },
        }

        normalized = normalize_message_to_canonical_v2(payload)

        self.assertEqual(normalized["group_id"], "group-1")
        self.assertEqual(normalized["relations"]["thread_id"], "thread-1")
        self.assertEqual(normalized["content"]["text"], "Need input on this draft.")
        self.assertEqual(normalized["flow_type"], "run")
        self.assertEqual(normalized["message_type"], "analysis")
        self.assertEqual(normalized["extensions"]["legacy_metadata"]["client_request_id"], "req-1")

    def test_normalize_legacy_targeted_message_preserves_target(self) -> None:
        payload = {
            "group_id": "group-2",
            "message_type": "proposal",
            "content": {
                "text": "@agent-self please take this.",
                "metadata": {
                    "target_agent_id": "agent-self",
                },
                "mentions": [
                    {
                        "mention_type": "agent",
                        "mention_id": "agent-self",
                        "display_text": "@Agent Self",
                    }
                ],
            },
        }

        normalized = normalize_message_to_canonical_v2(payload)

        self.assertEqual(normalized["flow_type"], "run")
        self.assertEqual(normalized["message_type"], "proposal")
        self.assertEqual(normalized["routing"]["target"]["agent_id"], "agent-self")
        self.assertEqual(normalized["routing"]["mentions"][0]["mention_id"], "agent-self")

    def test_normalize_current_message_keeps_shape(self) -> None:
        payload = {
            "id": "msg-v2",
            "group_id": "group-3",
            "author": {"agent_id": "agent-7"},
            "author_kind": "compat_agent",
            "flow_type": "result",
            "message_type": "decision",
            "status_block": {"kind": "visible_status", "label": "done"},
            "context_block": {"group_context": {"topic": "event-schema"}},
            "relations": {"thread_id": "thread-3", "parent_message_id": None},
            "content": {"text": "Decision recorded.", "payload": {"decision": "use_postgres"}, "blocks": [], "attachments": []},
            "routing": {"target": {"agent_id": None}, "mentions": []},
            "extensions": {"source": "unit-test", "custom": {"system_event": True}},
        }

        normalized = normalize_message_to_canonical_v2(payload)

        self.assertEqual(normalized["id"], "msg-v2")
        self.assertEqual(normalized["group_id"], "group-3")
        self.assertEqual(normalized["author"]["agent_id"], "agent-7")
        self.assertEqual(normalized["author_kind"], "compat_agent")
        self.assertEqual(normalized["flow_type"], "result")
        self.assertEqual(normalized["message_type"], "decision")
        self.assertEqual(normalized["status_block"]["label"], "done")
        self.assertEqual(normalized["context_block"]["group_context"]["topic"], "event-schema")


if __name__ == "__main__":
    unittest.main()
