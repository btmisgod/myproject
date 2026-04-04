from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone
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
EVENTS_PATH = RUNTIME_DIR / "events.jsonl"
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
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def respond_html(handler: BaseHTTPRequestHandler, html: str, status: int = 200) -> None:
    body = html.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
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


def append_event(source: str, kind: str, **payload: Any) -> None:
    ensure_dir(EVENTS_PATH.parent)
    event = {
        "timestamp": utc_now(),
        "source": source,
        "kind": kind,
        **payload,
    }
    with EVENTS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def load_events(limit: int = 120) -> list[dict[str, Any]]:
    if not EVENTS_PATH.exists():
        return synthesize_events(limit=limit)
    events: list[dict[str, Any]] = []
    with EVENTS_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            try:
                events.append(json.loads(text))
            except json.JSONDecodeError:
                continue
    if not events:
        return synthesize_events(limit=limit)
    return sorted(events, key=lambda item: item.get("timestamp") or "", reverse=True)[:limit]


def synthesize_events(limit: int = 60) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    files = sorted(RESULTS_DIR.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)[: max(1, limit // 2)]
    for path in files:
        result = load_json(path, {})
        task_id = str(result.get("task_id") or path.stem)
        timestamp = str(result.get("executed_at") or utc_now())
        summary = str(result.get("summary") or "")
        status = str(result.get("task_status") or "unknown")
        events.append(
            {
                "timestamp": timestamp,
                "source": "architect",
                "kind": "task_dispatched_history",
                "task_id": task_id,
                "title": task_id,
                "message": "历史任务补录",
                "goal": summary,
            }
        )
        events.append(
            {
                "timestamp": timestamp,
                "source": "server",
                "kind": "task_finished_history",
                "task_id": task_id,
                "status": status,
                "summary": summary,
                "blocker": str(result.get("blocker") or ""),
            }
        )
    return events[:limit]


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def bucket_start(timestamp: str | None) -> str:
    moment = parse_iso(timestamp)
    if moment is None:
        moment = datetime.now(timezone.utc)
    moment = moment.astimezone(timezone.utc)
    minute = 0 if moment.minute < 30 else 30
    bucket = moment.replace(minute=minute, second=0, microsecond=0)
    return bucket.isoformat()


def build_half_hour_summaries(events: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for event in events:
        start = bucket_start(event.get("timestamp"))
        bucket = buckets.setdefault(
            start,
            {
                "bucket_start": start,
                "architect_count": 0,
                "server_count": 0,
                "completed_count": 0,
                "blocked_count": 0,
                "tasks": [],
            },
        )
        if event.get("source") == "architect":
            bucket["architect_count"] += 1
        if event.get("source") == "server":
            bucket["server_count"] += 1
        status = str(event.get("status") or "")
        if status == "completed":
            bucket["completed_count"] += 1
        if status == "blocked":
            bucket["blocked_count"] += 1
        task_id = str(event.get("task_id") or "")
        if task_id and task_id not in bucket["tasks"]:
            bucket["tasks"].append(task_id)
    summaries: list[dict[str, Any]] = []
    for start in sorted(buckets.keys(), reverse=True)[:limit]:
        bucket = buckets[start]
        dt = parse_iso(start) or datetime.now(timezone.utc)
        end = dt + timedelta(minutes=30)
        tasks = "、".join(bucket["tasks"][:3]) or "无"
        message = (
            f"{dt.astimezone().strftime('%H:%M')} - {end.astimezone().strftime('%H:%M')} "
            f"接收 {bucket['architect_count']} 次指令，服务器记录 {bucket['server_count']} 次事件，"
            f"完成 {bucket['completed_count']} 个任务，阻塞 {bucket['blocked_count']} 个。"
            f" 主要任务：{tasks}"
        )
        summaries.append(
            {
                "bucket_start": start,
                "message": message,
            }
        )
    return summaries


def ui_log_entry(event: dict[str, Any]) -> dict[str, Any]:
    timestamp = str(event.get("timestamp") or "")
    task_id = str(event.get("task_id") or "")
    title = str(event.get("title") or task_id or event.get("kind") or "event")
    summary = str(event.get("summary") or event.get("message") or event.get("goal") or "")
    blocker = str(event.get("blocker") or "")
    status = str(event.get("status") or event.get("kind") or "")
    return {
        "timestamp": timestamp,
        "task_id": task_id,
        "title": title,
        "status": status,
        "summary": summary,
        "blocker": blocker,
    }


def sanitize_task(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": task.get("task_id"),
        "title": task.get("title"),
        "goal": task.get("goal"),
        "status": task.get("status"),
        "received_at": task.get("received_at"),
        "started_at": task.get("started_at"),
        "finished_at": task.get("finished_at"),
    }


def sanitize_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": result.get("task_id"),
        "task_status": result.get("task_status"),
        "summary": result.get("summary"),
        "blocker": result.get("blocker"),
        "changed_files": result.get("changed_files") or [],
        "tests": result.get("tests") or [],
        "executed_at": result.get("executed_at"),
    }


def build_ui_snapshot() -> dict[str, Any]:
    state = load_state()
    current_task = load_json(TASK_PATH, {})
    last_result = load_json(RESULT_PATH, {})
    events = load_events(limit=160)
    architect_logs = [ui_log_entry(event) for event in events if event.get("source") == "architect"][:24]
    server_logs = [ui_log_entry(event) for event in events if event.get("source") == "server"][:24]
    summaries = build_half_hour_summaries(events, limit=10)
    return {
        "worker_id": WORKER_ID,
        "state": state,
        "current_task": sanitize_task(current_task),
        "last_result": sanitize_result(last_result),
        "summaries": summaries,
        "architect_logs": architect_logs,
        "server_logs": server_logs,
        "updated_at": utc_now(),
    }


def dashboard_html() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Remote Codex Executor</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7fb;
      --panel: #ffffff;
      --ink: #1f2937;
      --muted: #6b7280;
      --line: #e5e7eb;
      --accent: #2563eb;
      --accent-soft: #dbeafe;
      --good: #166534;
      --good-soft: #dcfce7;
      --warn: #92400e;
      --warn-soft: #fef3c7;
      --bad: #991b1b;
      --bad-soft: #fee2e2;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", "PingFang SC", "Noto Sans SC", sans-serif;
      background: linear-gradient(180deg, #eef2ff 0%, var(--bg) 22%, var(--bg) 100%);
      color: var(--ink);
    }
    .page {
      max-width: 1320px;
      margin: 0 auto;
      padding: 28px 20px 40px;
    }
    .hero, .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
    }
    .hero {
      padding: 22px 24px 18px;
      margin-bottom: 18px;
    }
    .hero-top {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
      flex-wrap: wrap;
    }
    .title {
      margin: 0;
      font-size: 30px;
      font-weight: 760;
      letter-spacing: -0.02em;
    }
    .subtitle {
      margin: 8px 0 0;
      color: var(--muted);
      font-size: 14px;
    }
    .status-badges {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    .badge {
      border-radius: 999px;
      padding: 8px 12px;
      font-size: 13px;
      border: 1px solid var(--line);
      background: #f9fafb;
    }
    .badge.good { background: var(--good-soft); color: var(--good); border-color: #bbf7d0; }
    .badge.warn { background: var(--warn-soft); color: var(--warn); border-color: #fde68a; }
    .badge.bad { background: var(--bad-soft); color: var(--bad); border-color: #fecaca; }
    .hero-grid {
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
    }
    .stat {
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      background: linear-gradient(180deg, #ffffff 0%, #fafbff 100%);
    }
    .stat-label {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }
    .stat-value {
      margin-top: 8px;
      font-size: 20px;
      font-weight: 700;
      word-break: break-word;
    }
    .panel {
      padding: 18px 18px 12px;
      margin-bottom: 18px;
    }
    .panel-title {
      margin: 0 0 12px;
      font-size: 18px;
      font-weight: 700;
    }
    .summary-list, .log-list {
      display: grid;
      gap: 10px;
    }
    .summary-item, .log-item {
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px 14px;
      background: #fcfcff;
    }
    .summary-meta, .log-meta {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 6px;
      flex-wrap: wrap;
    }
    .log-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
    }
    .log-item h4 {
      margin: 0 0 6px;
      font-size: 15px;
    }
    .log-item p {
      margin: 0;
      color: var(--ink);
      line-height: 1.5;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .empty {
      color: var(--muted);
      font-size: 14px;
      padding: 12px 4px;
    }
    @media (max-width: 900px) {
      .log-grid { grid-template-columns: 1fr; }
      .page { padding: 18px 14px 28px; }
      .title { font-size: 24px; }
    }
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <div class="hero-top">
        <div>
          <h1 class="title">Remote Codex 工作台</h1>
          <p class="subtitle">顶部按 30 分钟汇总简报，下面左侧展示架构师通讯日志，右侧展示服务器执行日志。</p>
        </div>
        <div class="status-badges" id="status-badges"></div>
      </div>
      <div class="hero-grid" id="hero-grid"></div>
    </section>

    <section class="panel">
      <h2 class="panel-title">简报日志（每 30 分钟汇总）</h2>
      <div class="summary-list" id="summary-list"></div>
    </section>

    <section class="log-grid">
      <section class="panel">
        <h2 class="panel-title">架构师通讯日志</h2>
        <div class="log-list" id="architect-list"></div>
      </section>
      <section class="panel">
        <h2 class="panel-title">服务器通讯日志</h2>
        <div class="log-list" id="server-list"></div>
      </section>
    </section>
  </div>
  <script>
    const badgeTone = (value) => {
      if (value === "ready" || value === "completed") return "good";
      if (value === "running" || value === "pending") return "warn";
      return "bad";
    };

    const safe = (value) => value ?? "";

    const renderEmpty = (el, text) => {
      el.innerHTML = `<div class="empty">${text}</div>`;
    };

    const renderLogs = (id, items) => {
      const el = document.getElementById(id);
      if (!items || !items.length) {
        renderEmpty(el, "暂无日志。");
        return;
      }
      el.innerHTML = items.map((item) => `
        <article class="log-item">
          <div class="log-meta">
            <span>${safe(item.timestamp)}</span>
            <span>${safe(item.status)}</span>
          </div>
          <h4>${safe(item.title || item.task_id || "事件")}</h4>
          <p>${safe(item.summary || item.blocker || "无补充说明")}</p>
        </article>
      `).join("");
    };

    const renderSummaries = (items) => {
      const el = document.getElementById("summary-list");
      if (!items || !items.length) {
        renderEmpty(el, "暂无汇总，等待新的任务与执行痕迹。");
        return;
      }
      el.innerHTML = items.map((item) => `
        <article class="summary-item">
          <div class="summary-meta">
            <span>${safe(item.bucket_start)}</span>
          </div>
          <div>${safe(item.message)}</div>
        </article>
      `).join("");
    };

    const renderHero = (snapshot) => {
      const state = snapshot.state || {};
      const currentTask = snapshot.current_task || {};
      const lastResult = snapshot.last_result || {};
      const badges = document.getElementById("status-badges");
      badges.innerHTML = [
        ["执行端", snapshot.worker_id || "unknown", ""],
        ["当前状态", state.status || "unknown", badgeTone(state.status || "unknown")],
        ["当前任务", state.current_task_id || "none", ""],
      ].map(([label, value, tone]) => `<span class="badge ${tone}">${label}：${safe(value)}</span>`).join("");

      const stats = [
        ["当前状态", state.status || "unknown"],
        ["当前任务", state.current_task_id || "无"],
        ["最近结果", state.last_result_status || "无"],
        ["最近摘要", state.last_result_summary || "无"],
        ["当前阻塞", state.current_blocker || "无"],
        ["心跳时间", state.last_heartbeat_at || "无"],
        ["任务开始", currentTask.started_at || state.last_task_started_at || "无"],
        ["任务结束", currentTask.finished_at || state.last_task_finished_at || "无"],
        ["最后结果文件", lastResult.task_id || "无"],
      ];
      document.getElementById("hero-grid").innerHTML = stats.map(([label, value]) => `
        <div class="stat">
          <div class="stat-label">${label}</div>
          <div class="stat-value">${safe(value)}</div>
        </div>
      `).join("");
    };

    async function load() {
      const response = await fetch("/ui-data", { cache: "no-store" });
      const payload = await response.json();
      renderHero(payload);
      renderSummaries(payload.summaries || []);
      renderLogs("architect-list", payload.architect_logs || []);
      renderLogs("server-list", payload.server_logs || []);
    }

    load().catch((error) => {
      document.getElementById("summary-list").innerHTML = `<div class="empty">页面加载失败：${error}</div>`;
    });
    setInterval(() => {
      load().catch(() => {});
    }, 15000);
  </script>
</body>
</html>
"""


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
    append_event(
        "server",
        "task_running",
        task_id=task.get("task_id"),
        title=task.get("title"),
        status="running",
        summary="服务器开始执行任务",
    )
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
    append_event(
        "server",
        "task_finished",
        task_id=task.get("task_id"),
        title=task.get("title"),
        status=terminal,
        summary=result.get("summary"),
        blocker=result.get("blocker"),
    )


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
        if parsed.path in {"", "/"}:
            respond_html(self, dashboard_html())
            return
        if parsed.path == "/ui-data":
            respond_json(self, build_ui_snapshot())
            return
        if parsed.path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
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
                append_event(
                    "architect",
                    "task_received",
                    task_id=task["task_id"],
                    title=task.get("title"),
                    message="架构师派发任务",
                    goal=task.get("goal"),
                    status="pending",
                )
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
    append_event("server", "service_started", status=load_state().get("status"), summary="executor service started")
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
