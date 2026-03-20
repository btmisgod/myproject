import json
from pathlib import Path


def test_message_protocol_v2_canary_fixture_has_expected_scenarios() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "message-protocol-v2-canary-cases.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert payload["canary_agent"] == "proto-v2-canary"
    names = [item["name"] for item in payload["scenarios"]]
    assert names == ["discussion", "targeted_task", "status", "decision", "self_echo"]

    for item in payload["scenarios"]:
      message = item["message"]
      assert "container" in message
      assert "author" in message
      assert "relations" in message
      assert "body" in message
      assert "semantics" in message
      assert "routing" in message
      assert "extensions" in message
      assert message["container"]["group_id"] == "group-canary"
      assert isinstance(message["body"]["text"], str)
      assert message["semantics"]["kind"]
