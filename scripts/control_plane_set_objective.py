from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTROL_PLANE = ROOT / "docs" / "control-plane"
OBJECTIVE_PATH = CONTROL_PLANE / "OBJECTIVE.md"


def build_objective_markdown(
    *,
    title: str,
    outcome: str,
    stage: str,
    scope: str,
    acceptance: str,
    constraints: str,
    notes: str,
) -> str:
    return f"""# Active Objective Contract

## Purpose

This file is the lightweight, user-facing contract for the current staged long-running task.

Use it when the architect wants to set or replace the current staged objective without manually
rewriting the full control-plane docs.

## Current Objective

### Title

{title}

### Outcome

{outcome}

### Current Stage

{stage}

### Scope

{scope}

### Acceptance

{acceptance}

### Constraints

{constraints}

### Notes For The Local Controller

{notes}
"""


def read_text_argument(path_or_text: str) -> str:
    candidate = Path(path_or_text)
    if candidate.exists():
        return candidate.read_text(encoding="utf-8").strip()
    return path_or_text.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Set the active staged long-running control objective.")
    parser.add_argument("--title", required=True)
    parser.add_argument("--outcome", required=True, help="Plain text or a path to a text file.")
    parser.add_argument("--stage", required=True)
    parser.add_argument("--scope", required=True, help="Plain text or a path to a text file.")
    parser.add_argument("--acceptance", required=True, help="Plain text or a path to a text file.")
    parser.add_argument("--constraints", required=True, help="Plain text or a path to a text file.")
    parser.add_argument("--notes", default="Prefer minimal control-plane edits and keep exactly one active staged objective.")
    args = parser.parse_args()

    content = build_objective_markdown(
        title=args.title.strip(),
        outcome=read_text_argument(args.outcome),
        stage=args.stage.strip(),
        scope=read_text_argument(args.scope),
        acceptance=read_text_argument(args.acceptance),
        constraints=read_text_argument(args.constraints),
        notes=read_text_argument(args.notes),
    )
    OBJECTIVE_PATH.write_text(content, encoding="utf-8")
    print(f"updated {OBJECTIVE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
