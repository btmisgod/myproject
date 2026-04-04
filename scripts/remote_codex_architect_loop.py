from __future__ import annotations

import json
import os
import time
from hashlib import sha1
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


def default_policy() -> dict[str, Any]:
    return {
        "max_narrow_operations": 3,
        "max_fix_operations": 3,
        "design_review_after_repairs": 3,
        "max_repairs": 5,
        "result_history_limit": 3,
    }


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
        "controller_policy": {**default_policy(), **dict(raw.get("controller_policy") or {})},
        "design_docs": list(raw.get("design_docs") or []),
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
        "objective": {
            "title": objective.get("title"),
            "goal": objective.get("goal"),
            "controller_policy": objective.get("controller_policy"),
            "design_docs": objective.get("design_docs") or [],
        },
        "active_phase": {
            "phase_id": phase.get("phase_id"),
            "title": phase.get("title"),
            "goal": phase.get("goal"),
            "scope": phase.get("scope") or [],
            "acceptance": phase.get("acceptance") or [],
            "constraints": phase.get("constraints") or [],
            "notes": phase.get("notes") or "",
        },
        "server_state": summarize_server_state(server_state),
        "current_task": summarize_task(current_task),
        "latest_result": summarize_result(latest_result),
        "tracker": load_json(STATE_PATH, {}).get("repair_tracker", {}),
    }
    return template + "\n\nContext JSON:\n" + json.dumps(bundle, ensure_ascii=False, indent=2)


def summarize_server_state(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "worker_id": state.get("worker_id"),
        "default_workspace": state.get("default_workspace"),
        "status": state.get("status"),
        "current_task_id": state.get("current_task_id"),
        "last_task_started_at": state.get("last_task_started_at"),
        "last_task_finished_at": state.get("last_task_finished_at"),
        "last_result_status": state.get("last_result_status"),
        "last_result_summary": state.get("last_result_summary"),
        "current_blocker": state.get("current_blocker"),
        "updated_at": state.get("updated_at"),
    }


def summarize_task(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": task.get("task_id"),
        "title": task.get("title"),
        "goal": task.get("goal"),
        "status": task.get("status"),
        "received_at": task.get("received_at"),
        "started_at": task.get("started_at"),
        "finished_at": task.get("finished_at"),
    }


def summarize_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": result.get("task_id"),
        "task_status": result.get("task_status"),
        "summary": result.get("summary"),
        "blocker": result.get("blocker"),
        "changed_files": result.get("changed_files") or [],
        "tests": result.get("tests") or [],
        "executed_at": result.get("executed_at"),
    }


def task_key(task: dict[str, Any]) -> str:
    parts = [
        str(task.get("task_id") or ""),
        str(task.get("status") or ""),
        str(task.get("received_at") or ""),
        str(task.get("started_at") or ""),
        str(task.get("finished_at") or ""),
    ]
    return "|".join(parts)


def result_key(result: dict[str, Any]) -> str:
    parts = [
        str(result.get("task_id") or ""),
        str(result.get("task_status") or ""),
        str(result.get("executed_at") or ""),
        str(result.get("summary") or ""),
        str(result.get("blocker") or ""),
    ]
    return "|".join(parts)


def compact_signature(text: str) -> str:
    normalized = " ".join(text.lower().split()).strip()
    if not normalized:
        return ""
    return sha1(normalized.encode("utf-8")).hexdigest()[:12]


def derive_bug_signature(latest_result: dict[str, Any], current_task: dict[str, Any]) -> str:
    task_id = str((latest_result.get("task_id") or current_task.get("task_id") or "")).strip().lower()
    blocker = str(latest_result.get("blocker") or "").strip()
    summary = str(latest_result.get("summary") or "").strip()
    candidate = blocker or summary or task_id
    if task_id and candidate:
        candidate = f"{task_id}|{candidate}"
    return compact_signature(candidate)


def is_infra_blocker(text: str) -> bool:
    lowered = text.lower()
    return any(
        token in lowered
        for token in [
            "401 unauthorized",
            "http_error: 401",
            "usage limit",
            "rate limit",
            "missing bearer",
            "authentication",
            "executor_busy",
            "connection refused",
            "timed out",
        ]
    )


def ensure_state_snapshot(objective: dict[str, Any], phase: dict[str, Any]) -> dict[str, Any]:
    snapshot = load_json(STATE_PATH, {})
    snapshot.setdefault("repair_tracker", {})
    snapshot.setdefault("last_observed", {})
    snapshot.update(
        {
            "objective_title": objective.get("title"),
            "current_phase_index": objective.get("current_phase_index"),
            "current_phase_id": phase.get("phase_id"),
            "current_phase_title": phase.get("title"),
            "phase_count": len(objective.get("phases") or []),
            "updated_at": utc_now(),
        }
    )
    save_json(STATE_PATH, snapshot)
    return snapshot


def update_last_observed(server_state: dict[str, Any], current_task: dict[str, Any], latest_result: dict[str, Any]) -> None:
    snapshot = load_json(STATE_PATH, {})
    snapshot["last_observed"] = {
        "server_status": server_state.get("status"),
        "current_task_key": task_key(current_task),
        "latest_result_key": result_key(latest_result),
        "updated_at": utc_now(),
    }
    save_json(STATE_PATH, snapshot)


def mark_result_handled(latest_result: dict[str, Any]) -> None:
    key = result_key(latest_result)
    if not key:
        return
    snapshot = load_json(STATE_PATH, {})
    snapshot["last_handled_result_key"] = key
    save_json(STATE_PATH, snapshot)


def should_skip_codex(server_state: dict[str, Any], current_task: dict[str, Any], latest_result: dict[str, Any]) -> tuple[bool, str]:
    snapshot = load_json(STATE_PATH, {})
    last_observed = snapshot.get("last_observed", {})
    current_task_key = task_key(current_task)
    latest_result_key = result_key(latest_result)
    if server_state.get("status") in {"running", "pending"}:
        if current_task_key and current_task_key == last_observed.get("current_task_key"):
            return True, "task still running with no visible state change"
    handled_result_key = snapshot.get("last_handled_result_key")
    if server_state.get("status") == "ready" and latest_result_key and latest_result_key == handled_result_key:
        if not current_task or current_task.get("status") in {None, "", "completed", "blocked", "partial"}:
            return True, "no new result since last handled outcome"
    return False, ""


def reset_repair_tracker(reason: str) -> None:
    snapshot = load_json(STATE_PATH, {})
    snapshot["repair_tracker"] = {
        "active_signature": None,
        "narrow_operations": 0,
        "fix_operations": 0,
        "repair_cycles": 0,
        "cycle_has_fix": False,
        "last_result_key": None,
        "last_reset_reason": reason,
        "updated_at": utc_now(),
    }
    save_json(STATE_PATH, snapshot)


def current_tracker() -> dict[str, Any]:
    snapshot = load_json(STATE_PATH, {})
    tracker = dict(snapshot.get("repair_tracker") or {})
    if not tracker:
        tracker = {
            "active_signature": None,
            "narrow_operations": 0,
            "fix_operations": 0,
            "repair_cycles": 0,
            "cycle_has_fix": False,
            "last_result_key": None,
            "updated_at": utc_now(),
        }
    return tracker


def persist_tracker(tracker: dict[str, Any]) -> None:
    snapshot = load_json(STATE_PATH, {})
    tracker["updated_at"] = utc_now()
    snapshot["repair_tracker"] = tracker
    save_json(STATE_PATH, snapshot)


def maybe_track_failure(latest_result: dict[str, Any]) -> None:
    if not latest_result:
        return
    status = str(latest_result.get("task_status") or "")
    signature = derive_bug_signature(latest_result, {})
    tracker = current_tracker()
    latest_key = result_key(latest_result)
    if status == "completed":
        reset_repair_tracker("latest result completed")
        snapshot = load_json(STATE_PATH, {})
        snapshot["last_handled_result_key"] = latest_key
        save_json(STATE_PATH, snapshot)
        return
    if status not in {"blocked", "partial"}:
        return
    if tracker.get("last_result_key") == latest_key:
        return
    if signature and signature != tracker.get("active_signature"):
        tracker = {
            "active_signature": signature,
            "narrow_operations": 0,
            "fix_operations": 0,
            "repair_cycles": 0,
            "cycle_has_fix": False,
            "last_result_key": latest_key,
        }
    else:
        tracker["last_result_key"] = latest_key
    persist_tracker(tracker)


def enforce_failure_limits(objective: dict[str, Any], latest_result: dict[str, Any]) -> tuple[bool, str]:
    tracker = current_tracker()
    policy = objective.get("controller_policy") or default_policy()
    status = str(latest_result.get("task_status") or "")
    blocker_text = str(latest_result.get("blocker") or latest_result.get("summary") or "")
    if status in {"blocked", "partial"} and is_infra_blocker(blocker_text):
        return True, f"infrastructure/auth blocker: {blocker_text}"
    repairs = int(tracker.get("repair_cycles") or 0)
    if repairs >= int(policy.get("max_repairs") or 5):
        return True, f"same failure exceeded max repairs ({repairs})"
    if repairs >= int(policy.get("design_review_after_repairs") or 3):
        return True, f"design review required after {repairs} repair cycles"
    return False, ""


def apply_dispatch_limits(objective: dict[str, Any], decision: dict[str, Any], latest_result: dict[str, Any]) -> tuple[bool, str]:
    tracker = current_tracker()
    policy = objective.get("controller_policy") or default_policy()
    tracking = dict(decision.get("tracking") or {})
    operation_type = str(tracking.get("operation_type") or "other").lower()
    bug_signature = str(tracking.get("bug_signature") or "").strip() or derive_bug_signature(latest_result, {})
    if not bug_signature:
        return False, ""
    if tracker.get("active_signature") and tracker.get("active_signature") != bug_signature:
        tracker = {
            "active_signature": bug_signature,
            "narrow_operations": 0,
            "fix_operations": 0,
            "repair_cycles": 0,
            "cycle_has_fix": False,
            "last_result_key": tracker.get("last_result_key"),
        }
    else:
        tracker["active_signature"] = bug_signature
    if operation_type == "narrow":
        tracker["narrow_operations"] = int(tracker.get("narrow_operations") or 0) + 1
        if tracker["narrow_operations"] > int(policy.get("max_narrow_operations") or 3):
            persist_tracker(tracker)
            return True, f"same bug narrowing exceeded {policy.get('max_narrow_operations')} operations"
    elif operation_type in {"fix", "verify", "other"}:
        tracker["fix_operations"] = int(tracker.get("fix_operations") or 0) + 1
        if not tracker.get("cycle_has_fix"):
            tracker["repair_cycles"] = int(tracker.get("repair_cycles") or 0) + 1
            tracker["cycle_has_fix"] = True
        if tracker["fix_operations"] > int(policy.get("max_fix_operations") or 3):
            persist_tracker(tracker)
            return True, f"same blocker point exceeded {policy.get('max_fix_operations')} fix attempts"
        if int(tracker.get("repair_cycles") or 0) > int(policy.get("max_repairs") or 5):
            persist_tracker(tracker)
            return True, f"same failure exceeded {policy.get('max_repairs')} repair cycles"
    persist_tracker(tracker)
    return False, ""


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
    ensure_state_snapshot(objective, phase)
    state = http_request("GET", "/api/v1/state").get("state", {})
    current_task = http_request("GET", "/api/v1/task").get("task", {})
    latest_results = http_request("GET", "/api/v1/results?limit=1").get("results", [])
    latest_result = latest_results[0] if latest_results else {}
    maybe_track_failure(latest_result)
    hard_block, hard_reason = enforce_failure_limits(objective, latest_result)
    if hard_block:
        write_state("blocked", hard_reason)
        mark_result_handled(latest_result)
        update_last_observed(state, current_task, latest_result)
        return False
    skip_codex, skip_reason = should_skip_codex(state, current_task, latest_result)
    if skip_codex:
        write_state("idle")
        update_last_observed(state, current_task, latest_result)
        return False
    prompt = build_prompt(objective, state, current_task, latest_result)
    decision = codex_decide(prompt + "\n")
    save_json(LAST_DECISION_PATH, decision)
    action = decision.get("action")
    if action == "dispatch_task":
        local_block, local_reason = apply_dispatch_limits(objective, decision, latest_result)
        if local_block:
            write_state("blocked", local_reason)
            mark_result_handled(latest_result)
            update_last_observed(state, current_task, latest_result)
            return False
        payload = decision.get("task") or {}
        http_request("POST", "/api/v1/task", payload)
        write_state("running")
        update_last_observed(state, payload, latest_result)
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
            reset_repair_tracker("phase advanced")
            mark_result_handled(latest_result)
            update_last_observed(state, current_task, latest_result)
            return True
        write_state("completed")
        mark_result_handled(latest_result)
        update_last_observed(state, current_task, latest_result)
        return False
    if action == "blocked":
        write_state("blocked", str(decision.get("reason") or "architect marked blocked"))
        mark_result_handled(latest_result)
        update_last_observed(state, current_task, latest_result)
        return False
    write_state("idle")
    if not current_task or current_task.get("status") in {"completed", "blocked", "partial", None, ""}:
        mark_result_handled(latest_result)
    update_last_observed(state, current_task, latest_result)
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
