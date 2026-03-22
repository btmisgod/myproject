# Control-Plane Automation

This document describes how to turn the GitHub control plane into a continuously running server-side workflow.

## Goal

Run a server-side Codex worker that:

1. pulls the latest `myproject` control-plane docs
2. reads the current active objective
3. executes exactly one objective branch at a time
4. updates `SERVER_REPORT.md`
5. keeps a local worker heartbeat/state file

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
7. sleep until next poll window

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

This file is operational metadata only. It does not override control-plane docs.

## Polling

- Default cadence: every 2 minutes
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
