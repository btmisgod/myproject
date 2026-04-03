from __future__ import annotations

import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "docs" / "control-plane" / "SERVER_REPORT.md"
REPORT_REL = str(REPORT_PATH.relative_to(ROOT))


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)


def git_output_error(proc: subprocess.CompletedProcess[str]) -> str:
    return proc.stderr.strip() or proc.stdout.strip() or "git command failed"


def has_report_changes() -> bool:
    status = run(["git", "status", "--porcelain", REPORT_REL])
    if status.returncode != 0:
        raise SystemExit(git_output_error(status))
    return bool(status.stdout.strip())


def stage_report() -> None:
    add = run(["git", "add", REPORT_REL])
    if add.returncode != 0:
        raise SystemExit(git_output_error(add))


def commit_report(summary: str) -> bool:
    stage_report()
    status = run(["git", "status", "--porcelain", REPORT_REL])
    if status.returncode != 0:
        raise SystemExit(git_output_error(status))
    if not status.stdout.strip():
        return False
    commit_message = f"Update server report: {summary} @ {utc_timestamp()}"
    commit = run(["git", "commit", "-m", commit_message])
    if commit.returncode != 0:
        raise SystemExit(git_output_error(commit))
    return True


def restore_report(ref: str) -> None:
    restore = run(["git", "restore", "--source", ref, "--staged", "--worktree", "--", REPORT_REL])
    if restore.returncode != 0:
        raise SystemExit(git_output_error(restore))


def cleanup_publish_attempt(start_head: str) -> None:
    if (ROOT / ".git" / "rebase-merge").exists() or (ROOT / ".git" / "rebase-apply").exists():
        run(["git", "rebase", "--abort"])
    reset = run(["git", "reset", "--mixed", start_head])
    if reset.returncode != 0:
        raise SystemExit(git_output_error(reset))
    restore_report(start_head)


def continue_rebase_with_report(report_content: str) -> None:
    REPORT_PATH.write_text(report_content, encoding="utf-8")
    stage_report()
    cont = run(["git", "-c", "core.editor=true", "rebase", "--continue"])
    if cont.returncode != 0:
        raise SystemExit(git_output_error(cont))


def rebase_onto_remote(report_content: str) -> None:
    fetch = run(["git", "fetch", "origin", "main"])
    if fetch.returncode != 0:
        raise SystemExit(git_output_error(fetch))
    rebase = run(["git", "rebase", "FETCH_HEAD"])
    if rebase.returncode == 0:
        return
    if (ROOT / ".git" / "rebase-merge").exists() or (ROOT / ".git" / "rebase-apply").exists():
        continue_rebase_with_report(report_content)
        return
    raise SystemExit(git_output_error(rebase))


def push_with_retry(summary: str, report_content: str, start_head: str) -> int:
    for attempt in range(2):
        if has_report_changes():
            commit_report(summary)
        push = run(["git", "push", "origin", "main"])
        if push.returncode == 0:
            print("pushed_server_report")
            return 0
        message = git_output_error(push)
        if "fetch first" not in message and "non-fast-forward" not in message and "[rejected]" not in message:
            cleanup_publish_attempt(start_head)
            raise SystemExit(message)
        if attempt == 1:
            cleanup_publish_attempt(start_head)
            raise SystemExit(message)
        rebase_onto_remote(report_content)
        REPORT_PATH.write_text(report_content, encoding="utf-8")
    cleanup_publish_attempt(start_head)
    raise SystemExit("git push failed after retry")


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    parser = argparse.ArgumentParser(description="Commit and push the latest control-plane server report.")
    parser.add_argument("--summary", default="Update server report")
    args = parser.parse_args()

    if not REPORT_PATH.exists():
        raise SystemExit(f"missing report file: {REPORT_PATH}")

    if not has_report_changes():
        print("no_report_changes")
        return 0

    start_head = run(["git", "rev-parse", "HEAD"])
    if start_head.returncode != 0:
        raise SystemExit(git_output_error(start_head))
    report_content = REPORT_PATH.read_text(encoding="utf-8")
    return push_with_retry(args.summary, report_content, start_head.stdout.strip())


if __name__ == "__main__":
    raise SystemExit(main())
