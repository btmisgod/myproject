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


if __name__ == "__main__":
    unittest.main()
