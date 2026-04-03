from __future__ import annotations

import json
import os
import time
from pathlib import Path
from urllib import error, request

from remote_codex_common import ensure_dir, load_json, read_text, run_command, save_json, summarize_completed, utc_now


ROOT = Path(__file__).resolve().parents[1]
PROMPT_TEMPLATE = ROOT / "scripts" / "remote_codex_architect_prompt.txt"
RUNTIME_DIR = Path(os.environ.get("REMOTE_CODEX_ARCHITECT_RUNTIME_DIR", str(Path.home() / ".codex-remote-architect")))
OBJECTIVE_PATH = RUNTIME_DIR / "objective.json"
STATE_PATH = RUNTIME_DIR / "state.json"
LAST_DECISION_PATH = RUNTIME_DIR / "last-decision.json"
LAST_MESSAGE_PATH = RUNTIME_DIR / "last-codex-message.txt"
POLL_SECONDS = int(os.environ.get("REMOTE_CODEX_ARCHITECT_POLL_SECONDS", "120"))
SERVER_URL = os.environ.get("REMOTE_CODEX_SERVER_URL", "").rstrip("/")
SERVER_TOKEN = os.environ.get("REMOTE_CODEX_SERVER_TOKEN", "")
CODEX_BIN = os.environ.get("REMOTE_CODEX_ARCHITECT_CODEX_BIN", str(Path.home() / "AppData" / "Roaming" / "npm" / "codex.cmd"))
CODEX_TIMEOUT_SECONDS = int(os.environ.get("REMOTE_CODEX_ARCHITECT_CODEX_TIMEOUT_SECONDS", "900"))
RUN_ONCE = os.environ.get("REMOTE_CODEX_ARCHITECT_RUN_ONCE", "").strip() in {"1", "true", "TRUE", "yes", "YES"}


def http_request(method: str, path: str, payload: dict | None = None) -> dict:
    url = f"{SERVER_URL}{path}"
    body = None
    headers = {"Authorization": f"Bearer {SERVER_TOKEN}"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(url, method=method, data=body, headers=headers)
    with request.urlopen(req, timeout=30) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def write_state(status: str, blocker: str | None = None) -> None:
    save_json(
        STATE_PATH,
        {
            "status": status,
            "blocker": blocker,
            "updated_at": utc_now(),
        },
    )


def build_prompt(objective: dict, server_state: dict, current_task: dict, latest_result: dict) -> str:
    template = read_text(PROMPT_TEMPLATE)
    bundle = {
        "objective": objective,
        "server_state": server_state,
        "current_task": current_task,
        "latest_result": latest_result,
    }
    return template + "\n\nContext JSON:\n" + json.dumps(bundle, ensure_ascii=False, indent=2)


def parse_json_message(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("no json object found")
    return json.loads(text[start : end + 1])


def codex_decide(prompt: str) -> dict:
    cmd = [
        CODEX_BIN,
        "exec",
        "--dangerously-bypass-approvals-and-sandbox",
        "-C",
        str(ROOT),
        "--output-last-message",
        str(LAST_MESSAGE_PATH),
        "-",
    ]
    proc = run_command(cmd, cwd=ROOT, timeout=CODEX_TIMEOUT_SECONDS, stdin_text=prompt)
    output = summarize_completed(proc)
    if proc.returncode != 0:
        raise RuntimeError(output or f"codex exec failed with {proc.returncode}")
    final_message = read_text(LAST_MESSAGE_PATH, output)
    return parse_json_message(final_message)


def loop_once() -> None:
    objective = load_json(OBJECTIVE_PATH, {})
    if not objective:
        write_state("blocked", "missing objective.json")
        return
    state = http_request("GET", "/api/v1/state").get("state", {})
    current_task = http_request("GET", "/api/v1/task").get("task", {})
    latest_results = http_request("GET", "/api/v1/results?limit=1").get("results", [])
    latest_result = latest_results[0] if latest_results else {}
    prompt = build_prompt(objective, state, current_task, latest_result)
    decision = codex_decide(prompt + "\n")
    save_json(LAST_DECISION_PATH, decision)
    action = decision.get("action")
    if action == "dispatch_task":
        payload = decision.get("task") or {}
        http_request("POST", "/api/v1/task", payload)
        write_state("running")
        return
    if action == "completed":
        write_state("completed")
        return
    if action == "blocked":
        write_state("blocked", str(decision.get("reason") or "architect marked blocked"))
        return
    write_state("idle")


def main() -> int:
    ensure_dir(RUNTIME_DIR)
    if not SERVER_URL or not SERVER_TOKEN:
        write_state("blocked", "missing REMOTE_CODEX_SERVER_URL or REMOTE_CODEX_SERVER_TOKEN")
        return 1
    while True:
        try:
            loop_once()
        except error.HTTPError as exc:
            write_state("blocked", f"http_error: {exc.code}")
        except Exception as exc:  # noqa: BLE001
            write_state("blocked", str(exc))
        if RUN_ONCE:
            return 0
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
