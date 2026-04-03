# Active Objective Contract

## Purpose

This file is the lightweight, user-facing contract for the current staged long-running task.

Use it when the architect wants to set or replace the current staged objective without manually
rewriting the full control-plane docs.

## Current Objective

### Title

Stabilize the control-plane publish/adoption path, then resume the `community-skill` boundary repair phase.

### Outcome

The local architect-side controller and the server-side executor should work as a durable long-running pair:

- the server keeps consuming the latest architect objective
- the architect can continue issuing staged objectives without hand-editing large control docs
- the current downstream `community-skill` repair plan resumes only after the control-plane path is stable

### Current Stage

Control-plane stability and adoption proof.

### Scope

- `myproject` control-plane docs and scripts
- `myproject` local controller / server worker stability
- `community-skill` only after the current control-plane stability stage is accepted

### Acceptance

- the server worker publishes fresh `SERVER_REPORT.md` and `.runtime/worker-state.json` on the latest objective hash
- the local controller can continue driving the server with minimal architect-side updates
- after that, the active `community-skill` phase resumes:
  - provider-usage-first deliberation accounting
  - runtime no longer commands public replies
  - reply strategy owned by deliberation
  - `message_type` stays lightweight

### Constraints

- keep exactly one active staged objective
- preserve the already accepted single-agent onboarding baseline
- do not expand scope while the current stage is still blocked

### Notes For The Local Controller

- prefer updating `ARCHITECT_REVIEW.md` before rewriting `CONTROL.md`
- only update `CONTROL.md` when the current active objective summary itself must change
- treat this file as the highest-priority staged objective input after direct user chat instructions
