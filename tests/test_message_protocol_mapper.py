import unittest

from app.services.message_protocol_mapper import normalize_message_to_canonical_v2


class MessageProtocolMapperTests(unittest.TestCase):
    def test_normalize_legacy_discussion_message_to_v2(self) -> None:
        payload = {
            "group_id": "group-1",
            "thread_id": "thread-1",
            "message_type": "analysis",
            "content": {
                "text": "Need input on this draft.",
                "metadata": {
                    "intent": "inform",
                    "client_request_id": "req-1",
                },
            },
        }

        normalized = normalize_message_to_canonical_v2(payload)

        self.assertEqual(normalized["container"]["group_id"], "group-1")
        self.assertEqual(normalized["relations"]["thread_id"], "thread-1")
        self.assertEqual(normalized["body"]["text"], "Need input on this draft.")
        self.assertEqual(normalized["semantics"]["kind"], "analysis")
        self.assertEqual(normalized["semantics"]["intent"], "inform")
        self.assertEqual(normalized["extensions"]["client_request_id"], "req-1")

    def test_normalize_legacy_targeted_task_to_v2(self) -> None:
        payload = {
            "group_id": "group-2",
            "task_id": "task-9",
            "message_type": "proposal",
            "content": {
                "text": "@agent-self please take this.",
                "metadata": {
                    "intent": "request_action",
                    "target_agent_id": "agent-self",
                    "target_agent": "Agent Self",
                    "assignees": ["agent-self"],
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

        self.assertEqual(normalized["relations"]["task_id"], "task-9")
        self.assertEqual(normalized["semantics"]["kind"], "proposal")
        self.assertEqual(normalized["semantics"]["intent"], "request_action")
        self.assertEqual(normalized["routing"]["target"]["agent_id"], "agent-self")
        self.assertEqual(normalized["routing"]["assignees"], ["agent-self"])
        self.assertEqual(normalized["routing"]["mentions"][0]["mention_id"], "agent-self")

    def test_normalize_v2_message_keeps_canonical_shape(self) -> None:
        payload = {
            "id": "msg-v2",
            "container": {"group_id": "group-3"},
            "author": {"agent_id": "agent-7"},
            "relations": {"thread_id": "thread-3", "parent_message_id": None, "task_id": None},
            "body": {"text": "Decision recorded.", "blocks": [], "attachments": []},
            "semantics": {"kind": "decision", "intent": "decide", "topic": None},
            "routing": {"target": {"scope": None, "agent_id": None, "agent_label": None}, "mentions": [], "assignees": []},
            "extensions": {"client_request_id": "req-v2", "outbound_correlation_id": "corr-v2", "source": "unit-test", "custom": {"system_event": True}},
        }

        normalized = normalize_message_to_canonical_v2(payload)

        self.assertEqual(normalized["id"], "msg-v2")
        self.assertEqual(normalized["container"]["group_id"], "group-3")
        self.assertEqual(normalized["author"]["agent_id"], "agent-7")
        self.assertEqual(normalized["semantics"]["kind"], "decision")
        self.assertTrue(normalized["extensions"]["custom"]["system_event"])


if __name__ == "__main__":
    unittest.main()
