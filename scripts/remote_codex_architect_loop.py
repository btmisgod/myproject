from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
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
    current = load_json(STATE_PATH, {})
    current.update(
        {
            "status": status,
            "blocker": blocker,
            "updated_at": utc_now(),
        }
    )
    save_json(STATE_PATH, current)


def normalize_objective(raw: dict[str, Any]) -> dict[str, Any]:
    if not raw:
        return {}
    if raw.get("phases"):
        phases = raw["phases"]
    else:
        phase_id = str(raw.get("stage") or "phase-1")
        phases = [
            {
                "phase_id": phase_id,
                "title": str(raw.get("title") or phase_id),
                "goal": str(raw.get("goal") or ""),
                "scope": list(raw.get("scope") or []),
                "acceptance": list(raw.get("acceptance") or []),
                "constraints": list(raw.get("constraints") or []),
                "notes": str(raw.get("notes") or ""),
            }
        ]
    return {
        "title": str(raw.get("title") or phases[0].get("title") or "Untitled objective"),
        "goal": str(raw.get("goal") or ""),
        "phases": phases,
        "current_phase_index": int(raw.get("current_phase_index") or 0),
        "phase_history": list(raw.get("phase_history") or []),
        "updated_at": str(raw.get("updated_at") or utc_now()),
    }


def active_phase(objective: dict[str, Any]) -> dict[str, Any]:
    phases = objective.get("phases") or []
    if not phases:
        return {}
    index = int(objective.get("current_phase_index") or 0)
    index = max(0, min(index, len(phases) - 1))
    return phases[index]


def persist_objective(objective: dict[str, Any]) -> None:
    objective["updated_at"] = utc_now()
    save_json(OBJECTIVE_PATH, objective)


def advance_phase(objective: dict[str, Any], reason: str) -> bool:
    phases = objective.get("phases") or []
    index = int(objective.get("current_phase_index") or 0)
    if index >= len(phases) - 1:
        return False
    phase = phases[index]
    history = list(objective.get("phase_history") or [])
    history.append(
        {
            "phase_id": phase.get("phase_id"),
            "title": phase.get("title"),
            "completed_at": utc_now(),
            "reason": reason,
        }
    )
    objective["phase_history"] = history
    objective["current_phase_index"] = index + 1
    persist_objective(objective)
    return True


def build_prompt(objective: dict, server_state: dict, current_task: dict, latest_result: dict) -> str:
    template = read_text(PROMPT_TEMPLATE)
    phase = active_phase(objective)
    bundle = {
        "objective": objective,
        "active_phase": phase,
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


def loop_once() -> bool:
    objective = normalize_objective(load_json(OBJECTIVE_PATH, {}))
    if not objective:
        write_state("blocked", "missing objective.json")
        return False
    persist_objective(objective)
    phase = active_phase(objective)
    write_state("running" if load_json(STATE_PATH, {}).get("status") == "running" else "idle")
    state_snapshot = load_json(STATE_PATH, {})
    state_snapshot.update(
        {
            "objective_title": objective.get("title"),
            "current_phase_index": objective.get("current_phase_index"),
            "current_phase_id": phase.get("phase_id"),
            "current_phase_title": phase.get("title"),
            "phase_count": len(objective.get("phases") or []),
            "updated_at": utc_now(),
        }
    )
    save_json(STATE_PATH, state_snapshot)
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
        return False
    if action == "completed":
        if advance_phase(objective, str(decision.get("reason") or "phase completed")):
            next_phase = active_phase(objective)
            write_state("idle")
            state_snapshot = load_json(STATE_PATH, {})
            state_snapshot.update(
                {
                    "last_phase_completion_reason": str(decision.get("reason") or ""),
                    "current_phase_index": objective.get("current_phase_index"),
                    "current_phase_id": next_phase.get("phase_id"),
                    "current_phase_title": next_phase.get("title"),
                    "phase_count": len(objective.get("phases") or []),
                    "updated_at": utc_now(),
                }
            )
            save_json(STATE_PATH, state_snapshot)
            return True
        write_state("completed")
        return False
    if action == "blocked":
        write_state("blocked", str(decision.get("reason") or "architect marked blocked"))
        return False
    write_state("idle")
    return False


def main() -> int:
    ensure_dir(RUNTIME_DIR)
    if not SERVER_URL or not SERVER_TOKEN:
        write_state("blocked", "missing REMOTE_CODEX_SERVER_URL or REMOTE_CODEX_SERVER_TOKEN")
        return 1
    while True:
        try:
            immediate_continue = loop_once()
        except error.HTTPError as exc:
            write_state("blocked", f"http_error: {exc.code}")
            immediate_continue = False
        except Exception as exc:  # noqa: BLE001
            write_state("blocked", str(exc))
            immediate_continue = False
        if immediate_continue:
            continue
        if RUN_ONCE:
            return 0
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
