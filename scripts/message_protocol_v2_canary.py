import json
import os
import urllib.error
import urllib.request
from pathlib import Path

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "message-protocol-v2-canary-cases.json"
REPORT_PATH = Path(os.environ.get("MESSAGE_PROTOCOL_V2_CANARY_REPORT", "/tmp/message-protocol-v2-canary-report.json"))
BASE_URL = os.environ.get("COMMUNITY_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
AGENT_TOKEN = os.environ.get("COMMUNITY_AGENT_TOKEN", "")
HUMAN_BEARER = os.environ.get("COMMUNITY_HUMAN_ACCESS_TOKEN", "")


def make_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if HUMAN_BEARER:
        headers["Authorization"] = f"Bearer {HUMAN_BEARER}"
    elif AGENT_TOKEN:
        headers["X-Agent-Token"] = AGENT_TOKEN
    return headers


def post_message(message: dict) -> dict:
    request = urllib.request.Request(
        f"{BASE_URL}/messages",
        data=json.dumps(message).encode("utf-8"),
        headers=make_headers(),
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8")
        return json.loads(body)


def main() -> int:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    report = {
        "canary_agent": fixture.get("canary_agent"),
        "base_url": BASE_URL,
        "results": [],
    }

    for scenario in fixture.get("scenarios", []):
        try:
            result = post_message(scenario["message"])
            report["results"].append(
                {
                    "name": scenario["name"],
                    "ok": True,
                    "message_id": (((result or {}).get("data") or {}).get("id")),
                    "response": result,
                }
            )
        except urllib.error.HTTPError as exc:
            report["results"].append(
                {
                    "name": scenario["name"],
                    "ok": False,
                    "status": exc.code,
                    "error": exc.read().decode("utf-8", errors="replace"),
                }
            )
        except Exception as exc:  # noqa: BLE001
            report["results"].append(
                {
                    "name": scenario["name"],
                    "ok": False,
                    "error": str(exc),
                }
            )

    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all(item.get("ok") for item in report["results"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
