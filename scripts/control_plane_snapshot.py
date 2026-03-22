from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTROL_PLANE = ROOT / "docs" / "control-plane"
RUNTIME_DIR = CONTROL_PLANE / ".runtime"
STATE_PATH = RUNTIME_DIR / "worker-state.json"


def file_hash(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a local control-plane worker snapshot.")
    parser.add_argument("--status", required=True, choices=["idle", "running", "blocked", "completed"])
    parser.add_argument("--result", default="")
    parser.add_argument("--blocker", default="")
    args = parser.parse_args()

    control_path = CONTROL_PLANE / "CONTROL.md"
    architect_path = CONTROL_PLANE / "ARCHITECT_REVIEW.md"
    server_report_path = CONTROL_PLANE / "SERVER_REPORT.md"

    state = {
        "status": args.status,
        "current_objective": control_path.read_text(encoding="utf-8"),
        "control_hash": file_hash(control_path),
        "architect_review_hash": file_hash(architect_path),
        "server_report_hash": file_hash(server_report_path),
        "last_snapshot_at": utc_now(),
        "last_result": args.result,
        "current_blocker": args.blocker,
    }

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=True, indent=2), encoding="utf-8")
    print(str(STATE_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
