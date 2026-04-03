from __future__ import annotations

import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTROL_PLANE_DIR = ROOT / "docs" / "control-plane"
DEFAULT_DOCS = [
    CONTROL_PLANE_DIR / "OBJECTIVE.md",
    CONTROL_PLANE_DIR / "CONTROL.md",
    CONTROL_PLANE_DIR / "ARCHITECT_REVIEW.md",
]


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True, check=False)


def git_output_error(proc: subprocess.CompletedProcess[str]) -> str:
    return proc.stderr.strip() or proc.stdout.strip() or "git command failed"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def has_doc_changes(doc_paths: list[Path]) -> bool:
    args = ["git", "status", "--porcelain", "--", *[rel(path) for path in doc_paths]]
    status = run(args)
    if status.returncode != 0:
        raise SystemExit(git_output_error(status))
    return bool(status.stdout.strip())


def stage_docs(doc_paths: list[Path]) -> None:
    add = run(["git", "add", "--", *[rel(path) for path in doc_paths]])
    if add.returncode != 0:
        raise SystemExit(git_output_error(add))


def commit_docs(summary: str, doc_paths: list[Path]) -> bool:
    stage_docs(doc_paths)
    if not has_doc_changes(doc_paths):
        return False
    commit_message = f"Update control plane docs: {summary} @ {utc_timestamp()}"
    commit = run(["git", "commit", "-m", commit_message])
    if commit.returncode != 0:
        raise SystemExit(git_output_error(commit))
    return True


def restore_docs(ref: str, doc_paths: list[Path]) -> None:
    restore = run(["git", "restore", "--source", ref, "--staged", "--worktree", "--", *[rel(path) for path in doc_paths]])
    if restore.returncode != 0:
        raise SystemExit(git_output_error(restore))


def cleanup_publish_attempt(start_head: str, doc_paths: list[Path]) -> None:
    if (ROOT / ".git" / "rebase-merge").exists() or (ROOT / ".git" / "rebase-apply").exists():
        run(["git", "rebase", "--abort"])
    reset = run(["git", "reset", "--mixed", start_head])
    if reset.returncode != 0:
        raise SystemExit(git_output_error(reset))
    restore_docs(start_head, doc_paths)


def rebase_onto_remote(doc_contents: dict[Path, str]) -> None:
    fetch = run(["git", "fetch", "origin", "main"])
    if fetch.returncode != 0:
        raise SystemExit(git_output_error(fetch))
    rebase = run(["git", "rebase", "FETCH_HEAD"])
    if rebase.returncode == 0:
        return
    if (ROOT / ".git" / "rebase-merge").exists() or (ROOT / ".git" / "rebase-apply").exists():
        for path, content in doc_contents.items():
            path.write_text(content, encoding="utf-8")
        stage_docs(list(doc_contents.keys()))
        cont = run(["git", "-c", "core.editor=true", "rebase", "--continue"])
        if cont.returncode != 0:
            raise SystemExit(git_output_error(cont))
        return
    raise SystemExit(git_output_error(rebase))


def push_with_retry(summary: str, doc_paths: list[Path], start_head: str) -> int:
    doc_contents = {path: path.read_text(encoding="utf-8") for path in doc_paths}
    for attempt in range(2):
        if has_doc_changes(doc_paths):
            commit_docs(summary, doc_paths)
        push = run(["git", "push", "origin", "main"])
        if push.returncode == 0:
            print("pushed_control_plane_docs")
            return 0
        message = git_output_error(push)
        if "fetch first" not in message and "non-fast-forward" not in message and "[rejected]" not in message:
            cleanup_publish_attempt(start_head, doc_paths)
            raise SystemExit(message)
        if attempt == 1:
            cleanup_publish_attempt(start_head, doc_paths)
            raise SystemExit(message)
        rebase_onto_remote(doc_contents)
        for path, content in doc_contents.items():
            path.write_text(content, encoding="utf-8")
    cleanup_publish_attempt(start_head, doc_paths)
    raise SystemExit("git push failed after retry")


def main() -> int:
    parser = argparse.ArgumentParser(description="Commit and push selected control-plane docs.")
    parser.add_argument("--summary", default="architect update")
    parser.add_argument("--docs", nargs="*", default=[rel(path) for path in DEFAULT_DOCS])
    args = parser.parse_args()

    doc_paths = [ROOT / doc for doc in args.docs]
    for path in doc_paths:
        if not path.exists():
            raise SystemExit(f"missing control-plane doc: {path}")

    if not has_doc_changes(doc_paths):
        print("no_control_doc_changes")
        return 0

    start_head = run(["git", "rev-parse", "HEAD"])
    if start_head.returncode != 0:
        raise SystemExit(git_output_error(start_head))

    return push_with_retry(args.summary, doc_paths, start_head.stdout.strip())


if __name__ == "__main__":
    raise SystemExit(main())
