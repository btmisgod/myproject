# Workflow Lessons

This file records important workflow-design lessons learned while building the GitHub control-plane collaboration loop between the architect Codex and the server execution Codex.

These lessons are operational design constraints, not optional commentary. Reuse them the next time a similar multi-agent workflow is designed.

## 1. Control-plane docs are not the same as a running automation

Writing `CONTROL.md`, `SERVER_REPORT.md`, `ARCHITECT_REVIEW.md`, and prompt templates is necessary, but it does not mean the workflow is actually running.

The workflow is only truly active when all of the following exist:

- a real worker process on the server
- a polling loop
- a task execution entrypoint
- a state file or heartbeat
- a visible status return path

Do not claim "autopilot is running" unless there is execution evidence such as:

- a live worker service
- advancing loop timestamps
- a changing worker-state file
- new pushed reports

## 2. A startup prompt is still a real dependency

Even with a complete control plane, the first server-side autopilot loop may still require a one-time startup action.

Until a real background worker is installed and started, the system is still in a manually triggered mode.

The correct distinction is:

- control-plane docs = coordination protocol
- startup prompt = activation step
- background worker = actual automation

Do not blur those three layers together.

## 3. "Automatic execution" is not enough; status must be visible outside the server

If the worker runs but does not publish its state back to GitHub, humans still cannot observe progress without logging into the server.

The workflow is incomplete unless each meaningful loop publishes:

- `docs/control-plane/SERVER_REPORT.md`

If publishing fails, that failure must itself become the single current blocker.

## 4. Blocked state must not turn into a permanent no-op

A blocked worker still needs to retry the active objective on a bounded cadence.

Otherwise the system looks alive but is actually stalled.

Minimum requirement:

- blocked loops keep polling
- blocked loops periodically retry the current active objective
- blocked loops still record fresh state and status

Only retry with the same single objective. Do not silently branch into new work.

## 5. Updating worker code requires a worker restart

Changing control-plane documents is not enough when the bug is inside the worker itself.

If the worker process is long-running, new worker code does not take effect until the worker service is restarted.

This must be treated as a separate operational step:

1. update repo code
2. deploy or pull latest code
3. restart the worker service
4. verify the new behavior with logs and worker state

## 6. Distinguish local work from server work

The architect side may update docs, prompts, or local repositories without the server having executed anything new.

Reports must clearly separate:

- local preparation
- server execution
- evidence already seen
- evidence not yet seen

Do not summarize local prep work as if the server has already progressed.

## 7. Evidence must beat narrative

When there is tension between:

- what the workflow was supposed to do
- what the reports and logs prove

the evidence wins.

Use these as the priority evidence sources:

1. server worker state
2. pushed `SERVER_REPORT.md`
3. service logs
4. database evidence
5. local assumptions

## 8. The smallest fix applies to the workflow too

Do not overbuild orchestration.

When the workflow stalls, first ask:

- is the worker not started?
- is it not publishing?
- is it blocked and never retrying?
- is it running old code?

Fix the smallest layer that restores continuity before inventing a larger orchestration system.
