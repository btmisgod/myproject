import unittest

from app.services.channel_protocol_binding import read_group_protocol_binding, sanitize_group_metadata


class GroupProtocolPublicViewTests(unittest.TestCase):
    def test_read_group_protocol_binding_exposes_group_not_channel(self) -> None:
        protocol = read_group_protocol_binding({}, group_name="Demo Group", group_slug="demo-group")

        self.assertIn("group", protocol)
        self.assertNotIn("channel", protocol)
        self.assertEqual(protocol["group"]["group_name"], "Demo Group")
        self.assertEqual(protocol["group"]["group_slug"], "demo-group")

    def test_read_group_protocol_binding_drops_legacy_bootstrap_workflow_residue(self) -> None:
        metadata = {
            "community_protocols": {
                "channel": {
                    "summary": "legacy channel",
                    "execution_spec": {"stages": {"step1": {"stage_id": "step1"}}},
                    "workflow_id": "bootstrap-manager-only-workflow-v1",
                }
            }
        }

        protocol = read_group_protocol_binding(metadata, group_name="Demo Group", group_slug="demo-group")

        self.assertNotIn("execution_spec", protocol)
        self.assertNotIn("workflow_id", protocol)
        self.assertEqual(protocol["summary"], "legacy channel")

    def test_sanitize_group_metadata_drops_legacy_group_session_residue(self) -> None:
        metadata = {
            "community_v2": {
                "group_context": {"group_slug": "public-lobby"},
                "group_context_version": "group-context:legacy",
                "group_session": {"workflow_id": "bootstrap-manager-only-workflow-v1"},
            },
            "community_protocols": {
                "channel": {
                    "execution_spec": {"stages": {}},
                    "summary": "channel boundary",
                }
            },
        }

        cleaned = sanitize_group_metadata(metadata)

        self.assertNotIn("community_v2", cleaned)
        self.assertEqual(cleaned["community_protocols"]["channel"]["summary"], "channel boundary")
        self.assertNotIn("execution_spec", cleaned["community_protocols"]["channel"])


if __name__ == "__main__":
    unittest.main()
