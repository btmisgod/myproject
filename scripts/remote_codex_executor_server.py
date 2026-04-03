from __future__ import annotations

import json
import os
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from remote_codex_common import (
    ensure_dir,
    load_json,
    random_token,
    read_text,
    run_command,
    save_json,
    summarize_completed,
    utc_now,
)


HOST = os.environ.get("REMOTE_CODEX_EXECUTOR_HOST", "0.0.0.0")
PORT = int(os.environ.get("REMOTE_CODEX_EXECUTOR_PORT", "18789"))
RUNTIME_DIR = Path(os.environ.get("REMOTE_CODEX_EXECUTOR_RUNTIME_DIR", str(Path.home() / ".codex-remote-executor")))
STATE_PATH = RUNTIME_DIR / "state.json"
TASK_PATH = RUNTIME_DIR / "current_task.json"
RESULT_PATH = RUNTIME_DIR / "last_result.json"
RESULTS_DIR = RUNTIME_DIR / "results"
TOKEN_PATH = RUNTIME_DIR / "auth-token.txt"
DEFAULT_WORKSPACE = Path(os.environ.get("REMOTE_CODEX_EXECUTOR_DEFAULT_WORKSPACE", "/root/agent-community"))
CODEX_BIN = os.environ.get("REMOTE_CODEX_EXECUTOR_CODEX_BIN", "codex")
CODEX_TIMEOUT_SECONDS = int(os.environ.get("REMOTE_CODEX_EXECUTOR_CODEX_TIMEOUT_SECONDS", "1800"))
POLL_SECONDS = int(os.environ.get("REMOTE_CODEX_EXECUTOR_POLL_SECONDS", "5"))
WORKER_ID = os.environ.get("REMOTE_CODEX_EXECUTOR_WORKER_ID", "server-primary")


def auth_token() -> str:
    env_token = os.environ.get("REMOTE_CODEX_EXECUTOR_TOKEN", "").strip()
    if env_token:
        return env_token
    if TOKEN_PATH.exists():
        return TOKEN_PATH.read_text(encoding="utf-8").strip()
    token = random_token()
    ensure_dir(TOKEN_PATH.parent)
    TOKEN_PATH.write_text(token + "\n", encoding="utf-8")
    try:
        os.chmod(TOKEN_PATH, 0o600)
    except OSError:
        pass
    return token


AUTH_TOKEN = auth_token()
EXECUTOR_LOCK = threading.Lock()


def default_state() -> dict[str, Any]:
    return {
        "worker_id": WORKER_ID,
        "default_workspace": str(DEFAULT_WORKSPACE),
        "status": "ready",
        "current_task_id": None,
        "last_task_started_at": None,
        "last_task_finished_at": None,
        "last_heartbeat_at": None,
        "last_result_status": None,
        "last_result_summary": None,
        "current_blocker": None,
        "updated_at": utc_now(),
    }


def load_state() -> dict[str, Any]:
    return load_json(STATE_PATH, default_state())


def save_state(payload: dict[str, Any]) -> None:
    payload["updated_at"] = utc_now()
    save_json(STATE_PATH, payload)


def require_auth(handler: BaseHTTPRequestHandler) -> bool:
    header = handler.headers.get("Authorization", "")
    if header != f"Bearer {AUTH_TOKEN}":
        respond_json(handler, {"ok": False, "error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
        return False
    return True


def respond_json(handler: BaseHTTPRequestHandler, payload: dict[str, Any], status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    raw = handler.rfile.read(length).decode("utf-8")
    return json.loads(raw)


def build_codex_prompt(task: dict[str, Any]) -> str:
    must_do = "\n".join(f"- {item}" for item in task.get("must_do", [])) or "- complete the requested task"
    must_not_do = "\n".join(f"- {item}" for item in task.get("must_not_do", [])) or "- do not expand scope"
    acceptance = "\n".join(f"- {item}" for item in task.get("acceptance", [])) or "- satisfy the task goal"
    extra = task.get("notes", "").strip()
    return f"""You are the server execution Codex in a long-running architect/executor system.

Execute exactly one current task.

Task title:
{task.get('title', '').strip()}

Task goal:
{task.get('goal', '').strip()}

Must do:
{must_do}

Must not do:
{must_not_do}

Acceptance:
{acceptance}

Additional notes:
{extra or '- none'}

Output format:
Return strict JSON only with keys:
- task_status: completed | blocked | partial
- summary: string
- changed_files: string[]
- commands: string[]
- tests: string[]
- blocker: string
"""


def parse_json_message(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if not text:
        raise ValueError("empty codex output")
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("no json object in codex output")
    return json.loads(text[start : end + 1])


def execute_task(task: dict[str, Any]) -> dict[str, Any]:
    task_id = str(task["task_id"])
    requested_workspace = task.get("cwd")
    workspace = Path(requested_workspace) if requested_workspace else DEFAULT_WORKSPACE
    if not workspace.exists():
        workspace = DEFAULT_WORKSPACE
    prompt = build_codex_prompt(task)
    message_path = RUNTIME_DIR / f"last-message-{task_id}.txt"
    cmd = [
        CODEX_BIN,
        "exec",
        "--dangerously-bypass-approvals-and-sandbox",
        "-C",
        str(workspace),
        "--output-last-message",
        str(message_path),
        "-",
    ]
    proc = run_command(cmd, cwd=workspace, timeout=CODEX_TIMEOUT_SECONDS, stdin_text=prompt + "\n")
    output = summarize_completed(proc)
    final_message = read_text(message_path, output)
    try:
        result = parse_json_message(final_message)
    except Exception as exc:  # noqa: BLE001
        result = {
            "task_status": "blocked",
            "summary": "executor could not parse Codex result as JSON",
            "changed_files": [],
            "commands": cmd,
            "tests": [],
            "blocker": f"{exc}: {final_message[:1000]}",
        }
    result["task_id"] = task_id
    result["worker_id"] = WORKER_ID
    result["requested_workspace"] = str(requested_workspace) if requested_workspace else None
    result["workspace"] = str(workspace)
    result["executed_at"] = utc_now()
    if output:
        existing_commands = result.get("commands") or []
        if isinstance(existing_commands, list):
            result["commands"] = existing_commands
        result["raw_exec_output"] = output[:4000]
    return result


def mark_task_running(task: dict[str, Any]) -> None:
    task["status"] = "running"
    task["started_at"] = utc_now()
    save_json(TASK_PATH, task)
    state = load_state()
    state.update(
        {
            "status": "running",
            "current_task_id": task.get("task_id"),
            "last_task_started_at": task["started_at"],
            "current_blocker": None,
            "last_heartbeat_at": utc_now(),
        }
    )
    save_state(state)


def finish_task(task: dict[str, Any], result: dict[str, Any]) -> None:
    terminal = result.get("task_status", "blocked")
    task["status"] = terminal
    task["finished_at"] = utc_now()
    task["result_path"] = str((RESULTS_DIR / f"{task['task_id']}.json"))
    save_json(TASK_PATH, task)
    save_json(RESULT_PATH, result)
    save_json(RESULTS_DIR / f"{task['task_id']}.json", result)
    state = load_state()
    state.update(
        {
            "status": "blocked" if terminal == "blocked" else "ready",
            "current_task_id": task.get("task_id") if terminal == "blocked" else None,
            "last_task_finished_at": task["finished_at"],
            "last_result_status": terminal,
            "last_result_summary": result.get("summary", ""),
            "current_blocker": result.get("blocker") if terminal == "blocked" else None,
            "last_heartbeat_at": utc_now(),
        }
    )
    save_state(state)


def worker_loop() -> None:
    ensure_dir(RUNTIME_DIR)
    ensure_dir(RESULTS_DIR)
    if not STATE_PATH.exists():
        save_state(default_state())
    while True:
        with EXECUTOR_LOCK:
            state = load_state()
            state["last_heartbeat_at"] = utc_now()
            save_state(state)
            task = load_json(TASK_PATH, {})
            if task and task.get("status") == "pending":
                mark_task_running(task)
                result = execute_task(task)
                finish_task(task, result)
        time.sleep(POLL_SECONDS)


class Handler(BaseHTTPRequestHandler):
    server_version = "RemoteCodexExecutor/0.1"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            state = load_state()
            respond_json(
                self,
                {
                    "ok": True,
                    "worker_id": WORKER_ID,
                    "status": state.get("status", "unknown"),
                    "current_task_id": state.get("current_task_id"),
                },
            )
            return
        if not require_auth(self):
            return
        if parsed.path == "/api/v1/state":
            respond_json(self, {"ok": True, "state": load_state()})
            return
        if parsed.path == "/api/v1/task":
            respond_json(self, {"ok": True, "task": load_json(TASK_PATH, {})})
            return
        if parsed.path == "/api/v1/results":
            params = parse_qs(parsed.query)
            limit = int((params.get("limit") or ["10"])[0])
            files = sorted(RESULTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
            payload = [load_json(path, {}) for path in files]
            respond_json(self, {"ok": True, "results": payload})
            return
        respond_json(self, {"ok": False, "error": "not_found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if not require_auth(self):
            return
        if parsed.path == "/api/v1/task":
            task = read_body(self)
            required = ["task_id", "title", "goal"]
            missing = [key for key in required if not task.get(key)]
            if missing:
                respond_json(self, {"ok": False, "error": f"missing task fields: {', '.join(missing)}"}, HTTPStatus.BAD_REQUEST)
                return
            with EXECUTOR_LOCK:
                state = load_state()
                current_task = load_json(TASK_PATH, {})
                if state.get("status") == "running" or (current_task and current_task.get("status") in {"pending", "running"}):
                    respond_json(self, {"ok": False, "error": "executor_busy", "state": state, "task": current_task}, HTTPStatus.CONFLICT)
                    return
                task["status"] = "pending"
                task["received_at"] = utc_now()
                save_json(TASK_PATH, task)
                state.update(
                    {
                        "status": "pending",
                        "current_task_id": task["task_id"],
                        "current_blocker": None,
                        "last_heartbeat_at": utc_now(),
                    }
                )
                save_state(state)
            respond_json(self, {"ok": True, "task": task})
            return
        respond_json(self, {"ok": False, "error": "not_found"}, HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def main() -> int:
    ensure_dir(RUNTIME_DIR)
    ensure_dir(RESULTS_DIR)
    if not STATE_PATH.exists():
        save_state(default_state())
    thread = threading.Thread(target=worker_loop, daemon=True)
    thread.start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
