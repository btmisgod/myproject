from __future__ import annotations

import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "docs" / "control-plane" / "SERVER_REPORT.md"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    parser = argparse.ArgumentParser(description="Commit and push the latest control-plane server report.")
    parser.add_argument("--summary", default="Update server report")
    args = parser.parse_args()

    if not REPORT_PATH.exists():
        raise SystemExit(f"missing report file: {REPORT_PATH}")

    status = run(["git", "status", "--porcelain", str(REPORT_PATH)])
    if status.returncode != 0:
        raise SystemExit(status.stderr.strip() or "git status failed")
    if not status.stdout.strip():
        print("no_report_changes")
        return 0

    add = run(["git", "add", str(REPORT_PATH)])
    if add.returncode != 0:
        raise SystemExit(add.stderr.strip() or "git add failed")

    commit_message = f"Update server report: {args.summary} @ {utc_timestamp()}"
    commit = run(["git", "commit", "-m", commit_message])
    if commit.returncode != 0:
        raise SystemExit(commit.stderr.strip() or commit.stdout.strip() or "git commit failed")

    push = run(["git", "push", "origin", "main"])
    if push.returncode != 0:
        raise SystemExit(push.stderr.strip() or push.stdout.strip() or "git push failed")

    print("pushed_server_report")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
