import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOLS = ROOT / "community" / "protocols"


def load_json(name: str) -> dict:
    return json.loads((PROTOCOLS / name).read_text(encoding="utf-8-sig"))


class ProtocolScaffoldTests(unittest.TestCase):
    def test_layer1_scope_uses_group_message_status_actions(self) -> None:
        layer1 = load_json("layer1.general.json")
        scope = set(layer1["scope"])
        self.assertIn("group.enter", scope)
        self.assertIn("message.post", scope)
        self.assertIn("status.report", scope)
        self.assertFalse(any(item.startswith("task.") for item in scope))

    def test_layer3_template_uses_group_boundary_placeholders(self) -> None:
        layer3 = load_json("layer3.channel.template.json")
        placeholders = set(layer3["sections"]["placeholders"].keys())
        self.assertIn("group_boundary", placeholders)
        self.assertIn("group_workflow", placeholders)
        self.assertNotIn("channel_purpose", placeholders)
        self.assertNotIn("allowed_topics", placeholders)

    def test_layer3_template_contains_bootstrap_monitoring_workflow(self) -> None:
        layer3 = load_json("layer3.channel.template.json")
        workflow = layer3["sections"]["workflow"]
        self.assertTrue(workflow["callable_by_agents"])
        self.assertEqual(workflow["state_machine"]["status_words"], ["pending", "running", "blocked", "ready", "completed"])
        self.assertEqual(workflow["state_machine"]["terminal_states"], ["completed", "blocked"])
        bootstrap = workflow["bootstrap_workflow"]
        self.assertEqual(bootstrap["step0"]["triggered_by"], "protocol_repair_or_new_bootstrap")
        self.assertEqual(bootstrap["step0"]["next_step"], "step1")
        self.assertEqual(bootstrap["step1"]["triggered_by"], "manager_publish_goal")
        self.assertEqual(bootstrap["step1"]["next_step"], "step2")
        self.assertEqual(bootstrap["step2"]["triggered_by"], "manager_check_capability")
        self.assertEqual(bootstrap["step2"]["next_step"], "step3")
        self.assertEqual(bootstrap["step3"]["triggered_by"], "manager_distribute_contract")
        self.assertEqual(bootstrap["step3"]["next_step"], "step4")
        self.assertEqual(bootstrap["step4"]["triggered_by"], "manager_publish_task_start")
        self.assertEqual(bootstrap["step4"]["next_step"], "formal_workflow")
        self.assertEqual(workflow["monitoring_rules"]["codex_role"], "observer_only")
        self.assertIn("adjust group protocol first", workflow["monitoring_rules"]["repair_order"])
        self.assertIn("coach the three test agents", workflow["monitoring_rules"]["codex_must_not"])
        self.assertIn("observe progression", workflow["monitoring_rules"]["codex_must"])


if __name__ == "__main__":
    unittest.main()
