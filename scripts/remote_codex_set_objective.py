from __future__ import annotations

import argparse
import os
from pathlib import Path

from remote_codex_common import save_json, utc_now


DEFAULT_RUNTIME_DIR = Path.home() / ".codex-remote-architect"
RUNTIME_DIR = Path(os.environ.get("REMOTE_CODEX_ARCHITECT_RUNTIME_DIR", str(DEFAULT_RUNTIME_DIR)))
OBJECTIVE_PATH = RUNTIME_DIR / "objective.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Set the local long-running remote Codex objective.")
    parser.add_argument("--title", required=True)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--scope", nargs="+", required=True)
    parser.add_argument("--acceptance", nargs="+", required=True)
    parser.add_argument("--constraints", nargs="+", required=True)
    args = parser.parse_args()

    payload = {
        "title": args.title,
        "goal": args.goal,
        "stage": args.stage,
        "scope": args.scope,
        "acceptance": args.acceptance,
        "constraints": args.constraints,
        "updated_at": utc_now(),
    }
    save_json(OBJECTIVE_PATH, payload)
    print(OBJECTIVE_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
