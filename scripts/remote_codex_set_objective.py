from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from remote_codex_common import save_json, utc_now


DEFAULT_RUNTIME_DIR = Path.home() / ".codex-remote-architect"
RUNTIME_DIR = Path(os.environ.get("REMOTE_CODEX_ARCHITECT_RUNTIME_DIR", str(DEFAULT_RUNTIME_DIR)))
OBJECTIVE_PATH = RUNTIME_DIR / "objective.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Set the local long-running remote Codex objective.")
    parser.add_argument("--objective-file")
    parser.add_argument("--title")
    parser.add_argument("--goal")
    parser.add_argument("--stage")
    parser.add_argument("--scope", nargs="+")
    parser.add_argument("--acceptance", nargs="+")
    parser.add_argument("--constraints", nargs="+")
    args = parser.parse_args()

    if args.objective_file:
        payload = json.loads(Path(args.objective_file).read_text(encoding="utf-8"))
        payload["updated_at"] = utc_now()
    else:
        required = {
            "title": args.title,
            "goal": args.goal,
            "stage": args.stage,
            "scope": args.scope,
            "acceptance": args.acceptance,
            "constraints": args.constraints,
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            parser.error(f"missing required arguments for single-phase objective: {', '.join(missing)}")
        payload = {
            "title": args.title,
            "goal": args.goal,
            "phases": [
                {
                    "phase_id": args.stage,
                    "title": args.title,
                    "goal": args.goal,
                    "scope": args.scope,
                    "acceptance": args.acceptance,
                    "constraints": args.constraints,
                    "notes": "",
                }
            ],
            "current_phase_index": 0,
            "phase_history": [],
            "updated_at": utc_now(),
        }
    save_json(OBJECTIVE_PATH, payload)
    print(OBJECTIVE_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
