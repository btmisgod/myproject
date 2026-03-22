# Control-Plane Automation

This document describes how to turn the GitHub control plane into a continuously running server-side workflow.

## Goal

Run a server-side Codex worker that:

1. pulls the latest `myproject` control-plane docs
2. reads the current active objective
3. executes exactly one objective branch at a time
4. updates `SERVER_REPORT.md`
5. keeps a local worker heartbeat/state file
6. publishes status updates back to GitHub so humans can see progress without logging into the server

The architect side remains responsible for updating `CONTROL.md` and `ARCHITECT_REVIEW.md`.

## Autopilot Loop

Recommended loop:

1. `git pull` latest `myproject` main
2. read:
   - `docs/control-plane/REPO_INDEX.md`
   - `docs/control-plane/CONTROL.md`
   - `docs/control-plane/OPERATING_RULES.md`
   - `docs/designlog/`
3. update local worker state
4. if current objective is unfinished, continue executing it
5. write `SERVER_REPORT.md`
6. update local worker state
7. publish the updated `SERVER_REPORT.md` to GitHub
8. sleep until next poll window

Blocked state must not become a permanent no-op. If the active objective is still blocked and control-plane docs have not changed, the worker should still retry the same objective on a bounded cadence instead of waiting forever for a doc edit.

## Local Worker State

The worker should keep a local file:

- `docs/control-plane/.runtime/worker-state.json`

Suggested fields:

- `status`
- `current_objective`
- `control_hash`
- `architect_review_hash`
- `server_report_hash`
- `last_loop_started_at`
- `last_loop_finished_at`
- `last_result`
- `current_blocker`
- `last_codex_run_at`

This file is operational metadata only. It does not override control-plane docs.

## Status Visibility

Autopilot is not considered complete until server progress is visible outside the server.

The worker should publish status after each meaningful loop by committing and pushing:

- `docs/control-plane/SERVER_REPORT.md`

Recommended helper:

- `scripts/control_plane_publish_status.py`

If push fails, the worker should:

1. leave the updated report in the repo working tree
2. record the push failure in `SERVER_REPORT.md`
3. keep exactly one blocker
4. avoid pretending the report is visible remotely

## Polling

- Default cadence: every 2 minutes
- Recommended blocked-objective retry cadence: every poll window unless a heavier local policy overrides it
- If a heavy task is already running, do not interrupt it
- Refresh at the next safe checkpoint

## Safety Rules

- Never run two parallel objective branches from one worker
- Never expand scope beyond the current active objective
- Always report exactly one current blocker if blocked
- Always prefer the smallest fix that keeps the active chain moving

## Completion Rule

The worker should stop only when one of these is true:

- the current active objective is fully complete and `CONTROL.md` changes to the next phase
- the architect side explicitly changes the objective
- the worker hits a blocker and writes it into `SERVER_REPORT.md`
