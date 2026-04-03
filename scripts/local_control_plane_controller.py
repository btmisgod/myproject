from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTROL_PLANE = ROOT / "docs" / "control-plane"
DEFAULT_RUNTIME_DIR = Path.home() / ".codex" / "control-plane-local-runtime"
RUNTIME_DIR = Path(os.environ.get("LOCAL_CONTROL_PLANE_RUNTIME_DIR", str(DEFAULT_RUNTIME_DIR)))
STATE_PATH = RUNTIME_DIR / "local-controller-state.json"
LOCK_PATH = RUNTIME_DIR / "local-controller.lock"
TRACE_PATH = RUNTIME_DIR / "local-controller-trace.log"
CONTROL_PATH = CONTROL_PLANE / "CONTROL.md"
ARCHITECT_PATH = CONTROL_PLANE / "ARCHITECT_REVIEW.md"
OBJECTIVE_PATH = CONTROL_PLANE / "OBJECTIVE.md"
REPORT_PATH = CONTROL_PLANE / "SERVER_REPORT.md"
PROMPT_PATH = ROOT / "scripts" / "local_control_plane_controller_prompt.txt"
CONTROL_DOC_PATHS = [
    CONTROL_PATH,
    ARCHITECT_PATH,
    OBJECTIVE_PATH,
]

POLL_SECONDS = int(os.environ.get("LOCAL_CONTROL_PLANE_POLL_SECONDS", "120"))
DEFAULT_CODEX_BIN = (
    str(Path.home() / "AppData" / "Roaming" / "npm" / "codex.cmd")
    if os.name == "nt"
    else "codex"
)
CODEX_BIN = os.environ.get("LOCAL_CONTROL_PLANE_CODEX_BIN", DEFAULT_CODEX_BIN)
MODEL = os.environ.get("LOCAL_CONTROL_PLANE_MODEL", "")
RUN_ONCE = os.environ.get("LOCAL_CONTROL_PLANE_RUN_ONCE", "0") == "1"
CODEX_TIMEOUT_SECONDS = int(os.environ.get("LOCAL_CONTROL_PLANE_CODEX_TIMEOUT_SECONDS", "600"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=check,
    )


def log(event: str, **kwargs: object) -> None:
    payload = {"ts": utc_now(), "event": event, **kwargs}
    print(json.dumps(payload, ensure_ascii=False), flush=True)
    try:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        with TRACE_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


def completed_output(proc: subprocess.CompletedProcess[str]) -> str:
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    return "\n".join(part for part in [stdout.strip(), stderr.strip()] if part).strip()


def git_pull_latest() -> None:
    run(["git", "fetch", "origin", "main"])
    run(["git", "reset", "--hard", "origin/main"])


def control_doc_changes() -> list[str]:
    status = run(
        ["git", "status", "--porcelain", "--", *[str(path.relative_to(ROOT)) for path in CONTROL_DOC_PATHS]],
        check=False,
    )
    if status.returncode != 0:
        return [status.stderr.strip() or status.stdout.strip() or "git status failed"]
    return [line for line in status.stdout.splitlines() if line.strip()]


def write_state(
    *,
    status: str,
    loop_started_at: str,
    loop_finished_at: str | None,
    last_result: str,
    current_objective_hash: str,
    current_control_hash: str,
    current_architect_hash: str,
    current_report_hash: str,
    current_blocker: str | None,
    last_publish_at: str | None,
) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    state = {
        "status": status,
        "last_loop_started_at": loop_started_at,
        "last_loop_finished_at": loop_finished_at,
        "last_result": last_result,
        "objective_hash": current_objective_hash,
        "control_hash": current_control_hash,
        "architect_review_hash": current_architect_hash,
        "server_report_hash": current_report_hash,
        "current_blocker": current_blocker,
        "last_publish_at": last_publish_at,
        "last_snapshot_at": utc_now(),
    }
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def run_codex_loop() -> tuple[bool, str]:
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    cmd = [
        CODEX_BIN,
        "exec",
        "--dangerously-bypass-approvals-and-sandbox",
        "-C",
        str(ROOT),
        "--output-last-message",
        str(RUNTIME_DIR / "last-local-controller-message.txt"),
        "-",
    ]
    if MODEL:
        cmd.extend(["-m", MODEL])
    try:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            input=prompt,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            timeout=CODEX_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        output = "\n".join(part for part in [str(stdout).strip(), str(stderr).strip()] if part).strip()
        return False, output or f"codex exec timed out after {CODEX_TIMEOUT_SECONDS}s"
    output = completed_output(proc)
    return proc.returncode == 0, output


def publish_control_docs() -> tuple[bool, str]:
    proc = subprocess.run(
        ["python", str(ROOT / "scripts" / "control_plane_publish_control_docs.py"), "--summary", "local controller update"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    output = completed_output(proc)
    return proc.returncode == 0, output


@contextmanager
def controller_lock() -> object:
    if os.name == "nt":
        import msvcrt

        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        with LOCK_PATH.open("w", encoding="utf-8") as lock_file:
            try:
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise SystemExit("local control-plane controller already running") from exc
            lock_file.write(str(os.getpid()))
            lock_file.flush()
            yield
    else:
        import fcntl

        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        with LOCK_PATH.open("w", encoding="utf-8") as lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise SystemExit("local control-plane controller already running") from exc
            lock_file.write(str(os.getpid()))
            lock_file.flush()
            yield


def loop_once(loop_number: int, last_publish_at: str | None) -> str | None:
    loop_started_at = utc_now()
    log("local_controller_loop_started", loop=loop_number)
    git_pull_latest()
    log("local_controller_git_sync_ok", loop=loop_number)

    write_state(
        status="running",
        loop_started_at=loop_started_at,
        loop_finished_at=None,
        last_result="loop_running",
        current_objective_hash=file_hash(OBJECTIVE_PATH),
        current_control_hash=file_hash(CONTROL_PATH),
        current_architect_hash=file_hash(ARCHITECT_PATH),
        current_report_hash=file_hash(REPORT_PATH),
        current_blocker=None,
        last_publish_at=last_publish_at,
    )

    codex_ok, codex_output = run_codex_loop()
    log("local_controller_codex_returned", loop=loop_number, ok=codex_ok)
    changes = control_doc_changes()
    log("local_controller_doc_change_scan", loop=loop_number, changes=len(changes))
    publish_result = ""
    publish_ok = True

    if changes:
        publish_ok, publish_result = publish_control_docs()
        if publish_ok:
            last_publish_at = utc_now()
            log("local_controller_publish_completed", loop=loop_number, output=publish_result)
        else:
            log("local_controller_publish_failed", loop=loop_number, output=publish_result)
    else:
        log("local_controller_no_changes", loop=loop_number)

    final_status = "blocked" if (not codex_ok or not publish_ok) else "completed"
    current_blocker = None if final_status == "completed" else (publish_result or codex_output or "controller loop failed")
    write_state(
        status=final_status,
        loop_started_at=loop_started_at,
        loop_finished_at=utc_now(),
        last_result="loop_complete" if final_status == "completed" else "loop_failed",
        current_objective_hash=file_hash(OBJECTIVE_PATH),
        current_control_hash=file_hash(CONTROL_PATH),
        current_architect_hash=file_hash(ARCHITECT_PATH),
        current_report_hash=file_hash(REPORT_PATH),
        current_blocker=current_blocker,
        last_publish_at=last_publish_at,
    )
    log("local_controller_state_written", loop=loop_number, status=final_status)

    if codex_output:
        log("local_controller_codex_output", loop=loop_number, output=codex_output)

    return last_publish_at


def main() -> int:
    loop_number = 0
    last_publish_at: str | None = None
    with controller_lock():
        while True:
            loop_number += 1
            try:
                last_publish_at = loop_once(loop_number, last_publish_at)
            except BaseException as exc:  # noqa: BLE001
                log("local_controller_loop_exception", loop=loop_number, error=str(exc))
                write_state(
                    status="blocked",
                    loop_started_at=utc_now(),
                    loop_finished_at=utc_now(),
                    last_result="loop_exception",
                    current_objective_hash=file_hash(OBJECTIVE_PATH),
                    current_control_hash=file_hash(CONTROL_PATH),
                    current_architect_hash=file_hash(ARCHITECT_PATH),
                    current_report_hash=file_hash(REPORT_PATH),
                    current_blocker=str(exc),
                    last_publish_at=last_publish_at,
                )
            if RUN_ONCE:
                break
            time.sleep(POLL_SECONDS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
