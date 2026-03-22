from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTROL_PLANE = ROOT / "docs" / "control-plane"
RUNTIME_DIR = CONTROL_PLANE / ".runtime"
STATE_PATH = RUNTIME_DIR / "worker-state.json"
REPORT_PATH = CONTROL_PLANE / "SERVER_REPORT.md"
CONTROL_PATH = CONTROL_PLANE / "CONTROL.md"
ARCHITECT_PATH = CONTROL_PLANE / "ARCHITECT_REVIEW.md"
REPO_INDEX_PATH = CONTROL_PLANE / "REPO_INDEX.md"
RULES_PATH = CONTROL_PLANE / "OPERATING_RULES.md"
DESIGNLOG_DIR = ROOT / "docs" / "designlog"
PROMPT_PATH = ROOT / "scripts" / "control_plane_worker_prompt.txt"
LOCK_PATH = RUNTIME_DIR / "worker.lock"

POLL_SECONDS = int(os.environ.get("CONTROL_PLANE_POLL_SECONDS", "120"))
CODEX_BIN = os.environ.get("CONTROL_PLANE_CODEX_BIN", "codex")
MODEL = os.environ.get("CONTROL_PLANE_MODEL", "")
RUN_ONCE = os.environ.get("CONTROL_PLANE_RUN_ONCE", "0") == "1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def log(event: str, **kwargs: object) -> None:
    payload = {"ts": utc_now(), "event": event, **kwargs}
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def read_required_docs() -> dict[str, object]:
    designlog_files = sorted(str(path.relative_to(ROOT)) for path in DESIGNLOG_DIR.rglob("*") if path.is_file())
    return {
        "repo_index": REPO_INDEX_PATH.read_text(encoding="utf-8"),
        "control": CONTROL_PATH.read_text(encoding="utf-8"),
        "rules": RULES_PATH.read_text(encoding="utf-8"),
        "designlog_files": designlog_files,
    }


def extract_current_objective(control_text: str) -> str:
    match = re.search(
        r"## Current Active Objective\s+(.*?)(?:\n## |\Z)",
        control_text,
        flags=re.S,
    )
    return match.group(1).strip() if match else ""


def extract_blocker(report_text: str) -> str:
    match = re.search(r"## Single Blocking Point\s+(.*?)(?:\n## |\Z)", report_text, flags=re.S)
    return match.group(1).strip() if match else ""


def update_report_heartbeat(report_text: str, heartbeat_lines: list[str]) -> str:
    section = "## Autopilot Heartbeat\n\n" + "\n".join(heartbeat_lines) + "\n\n"
    if "## Autopilot Heartbeat\n" in report_text:
        return re.sub(
            r"## Autopilot Heartbeat\s+.*?(?=\n## |\Z)",
            section.rstrip(),
            report_text,
            flags=re.S,
        )
    marker = "## Work Performed\n"
    if marker in report_text:
        return report_text.replace(marker, section + marker, 1)
    return report_text.rstrip() + "\n\n" + section


def write_worker_state(
    *,
    status: str,
    current_objective: str,
    control_hash: str,
    architect_review_hash: str,
    server_report_hash: str,
    loop_started_at: str,
    loop_finished_at: str | None,
    last_result: str,
    current_blocker: str,
) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    state = {
        "status": status,
        "current_objective": current_objective,
        "control_hash": control_hash,
        "architect_review_hash": architect_review_hash,
        "server_report_hash": server_report_hash,
        "last_loop_started_at": loop_started_at,
        "last_loop_finished_at": loop_finished_at,
        "last_result": last_result,
        "current_blocker": current_blocker,
        "last_snapshot_at": utc_now(),
    }
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def load_state() -> dict[str, object]:
    if not STATE_PATH.exists():
        return {}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def publish_report(summary: str) -> tuple[bool, str]:
    proc = subprocess.run(
        ["python3", str(ROOT / "scripts" / "control_plane_publish_status.py"), "--summary", summary],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    output = "\n".join(part for part in [proc.stdout.strip(), proc.stderr.strip()] if part).strip()
    return proc.returncode == 0, output


def set_push_failure_blocker(report_text: str, message: str) -> str:
    replacement = (
        "## Single Blocking Point\n\n"
        f"Publishing `docs/control-plane/SERVER_REPORT.md` back to GitHub failed on this server: `{message}`. "
        "Per control-plane publish rules, this push failure is the current single blocker.\n\n"
        "## Recommendation\n\n"
        "Next step after GitHub push access is restored: publish this report remotely, then continue the current active objective.\n"
    )
    return re.sub(
        r"## Single Blocking Point\s+.*?(?:\n## Recommendation\s+.*?(?=\n## |\Z)|\Z)",
        replacement.rstrip(),
        report_text,
        flags=re.S,
    )


def run_codex_loop() -> tuple[bool, str]:
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    cmd = [
        CODEX_BIN,
        "exec",
        "--dangerously-bypass-approvals-and-sandbox",
        "-C",
        str(ROOT),
        "--output-last-message",
        str(RUNTIME_DIR / "last-codex-message.txt"),
        "-",
    ]
    if MODEL:
        cmd.extend(["-m", MODEL])
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        input=prompt,
        text=True,
        capture_output=True,
        check=False,
    )
    output = "\n".join(part for part in [proc.stdout.strip(), proc.stderr.strip()] if part).strip()
    return proc.returncode == 0, output


@contextmanager
def worker_lock() -> object:
    import fcntl

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("w", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SystemExit("control-plane worker already running") from exc
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        yield


def git_pull_latest() -> None:
    run(["git", "pull", "--rebase", "origin", "main"])


def loop_once(loop_number: int) -> None:
    loop_started_at = utc_now()
    log("loop_started", loop=loop_number)

    git_pull_latest()
    docs = read_required_docs()
    control_text = str(docs["control"])
    current_objective = extract_current_objective(control_text)
    current_control_hash = file_hash(CONTROL_PATH)
    current_architect_hash = file_hash(ARCHITECT_PATH)
    report_text = REPORT_PATH.read_text(encoding="utf-8")
    blocker = extract_blocker(report_text)

    previous_state = load_state()
    previous_control_hash = str(previous_state.get("control_hash", ""))
    previous_architect_hash = str(previous_state.get("architect_review_hash", ""))
    previous_status = str(previous_state.get("status", ""))
    objective_changed = previous_control_hash != current_control_hash
    architect_changed = previous_architect_hash != current_architect_hash

    write_worker_state(
        status="running",
        current_objective=current_objective,
        control_hash=current_control_hash,
        architect_review_hash=current_architect_hash,
        server_report_hash=file_hash(REPORT_PATH),
        loop_started_at=loop_started_at,
        loop_finished_at=None,
        last_result="loop_running",
        current_blocker=blocker,
    )

    codex_ran = False
    codex_ok = True
    codex_output = ""
    if previous_status != "blocked" or objective_changed or architect_changed:
        codex_ran = True
        codex_ok, codex_output = run_codex_loop()
        log("codex_exec_completed", loop=loop_number, ok=codex_ok)
        report_text = REPORT_PATH.read_text(encoding="utf-8")
        blocker = extract_blocker(report_text)

    loop_finished_at = utc_now()
    heartbeat_lines = [
        f"- Loop: `{loop_number}`",
        f"- Poll interval seconds: `{POLL_SECONDS}`",
        f"- Last loop started at: `{loop_started_at}`",
        f"- Last loop finished at: `{loop_finished_at}`",
        f"- Current objective hash: `{current_control_hash}`",
        f"- Current worker status: `{'blocked' if blocker else 'running'}`",
        f"- Current blocker: `{blocker or 'none'}`",
        f"- Codex objective step ran this loop: `{str(codex_ran).lower()}`",
    ]
    report_text = update_report_heartbeat(report_text, heartbeat_lines)
    REPORT_PATH.write_text(report_text, encoding="utf-8")

    final_status = "blocked" if blocker else "running"
    final_result = "waiting_for_control_change" if final_status == "blocked" and not objective_changed else "loop_complete"

    write_worker_state(
        status=final_status,
        current_objective=current_objective,
        control_hash=current_control_hash,
        architect_review_hash=current_architect_hash,
        server_report_hash=file_hash(REPORT_PATH),
        loop_started_at=loop_started_at,
        loop_finished_at=loop_finished_at,
        last_result=final_result if codex_ok else "codex_exec_failed",
        current_blocker=blocker,
    )

    publish_ok, publish_output = publish_report(f"worker loop {loop_number}")
    if not publish_ok:
        report_text = REPORT_PATH.read_text(encoding="utf-8")
        report_text = set_push_failure_blocker(report_text, publish_output or "git push failed")
        REPORT_PATH.write_text(report_text, encoding="utf-8")
        write_worker_state(
            status="blocked",
            current_objective=current_objective,
            control_hash=current_control_hash,
            architect_review_hash=current_architect_hash,
            server_report_hash=file_hash(REPORT_PATH),
            loop_started_at=loop_started_at,
            loop_finished_at=utc_now(),
            last_result="blocked_on_report_push_failure",
            current_blocker=f"SERVER_REPORT.md push failed: {publish_output or 'git push failed'}",
        )
        log("publish_failed", loop=loop_number, output=publish_output)
    else:
        log("publish_completed", loop=loop_number, output=publish_output)

    if codex_ran and not codex_ok:
        log("codex_exec_output", loop=loop_number, output=codex_output)


def main() -> int:
    loop_number = 0
    with worker_lock():
        while True:
            loop_number += 1
            try:
                loop_once(loop_number)
            except Exception as exc:  # noqa: BLE001
                log("loop_exception", loop=loop_number, error=str(exc))
                loop_started_at = utc_now()
                current_objective = extract_current_objective(CONTROL_PATH.read_text(encoding="utf-8"))
                write_worker_state(
                    status="blocked",
                    current_objective=current_objective,
                    control_hash=file_hash(CONTROL_PATH),
                    architect_review_hash=file_hash(ARCHITECT_PATH),
                    server_report_hash=file_hash(REPORT_PATH),
                    loop_started_at=loop_started_at,
                    loop_finished_at=utc_now(),
                    last_result="loop_exception",
                    current_blocker=str(exc),
                )
            if RUN_ONCE:
                break
            time.sleep(POLL_SECONDS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
