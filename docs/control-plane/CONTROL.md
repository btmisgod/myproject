# CONTROL

## Long-Range Objective

Complete the Community project according to the design docs and run it successfully.
Complete the `community-skill` project so that installing it on a fresh OpenClaw instance automatically connects that agent to the community and lets it use community features correctly.
After both are complete, run a retrospective review. If the review is clean, end this task cycle.

## Current Active Objective

Stabilize the control-plane publish/adoption path on the latest architect objective before resuming downstream `community-skill` work.

The only active objective in this loop is:

- the server worker must keep heartbeat
- `git pull --rebase origin main` must remain healthy across loops
- control-plane report publishing must survive normal remote-main concurrency instead of falling back into a blocker state
- the next fresh `SERVER_REPORT.md` and `docs/control-plane/.runtime/worker-state.json` update must carry the current `CONTROL.md` hash `69634faf0c41de012bcf8eb9464b7ff0e223c70793b78138c84f755c1567fa58`
- status fields must stay internally consistent; do not publish `blocked` with `None.` and do not claim the worker remains `running` while status is `blocked`

Until that adoption report lands, do not count `community-skill` edits, tests, or "same branch" validation as progress for this objective.

After this objective is proven stable, the next objective remains the already-planned multi-agent boundary repair in `community-skill`:

- deliberation token accounting is trustworthy and provider-usage-first
- runtime no longer commands public reply behavior
- reply strategy is owned by the deliberation module
- `message_type` stays a light semantic field instead of a heavy control enum
- reciprocal multi-agent thread relay / auto-reply behavior is reduced by boundary fixes rather than by ad hoc hard rules

## Instruction Source

Priority order:

1. The latest user instruction in the main architect chat
2. This file: `CONTROL.md`
3. The latest minimal action in `ARCHITECT_REVIEW.md`

Rules:

- User chat instructions do not go directly to the server executor.
- The architect Codex must first sync them into the GitHub control-plane docs.
- The server executor trusts repo docs, not chat logs.

## Scope

Allowed repositories:

- `myproject`
- `community-skill`

Allowed areas:

- `myproject` code and docs related to the Community main chain, events, webhook, group, message, presence, and deployment
- `myproject` control-plane worker logic, runtime state handling, and safe publish behavior for control-plane docs
- `community-skill` code and docs related to onboarding, webhook, runtime, protocol adaptation, agent-side asset install, and automatic connection
- Deployment scripts, env templates, service configs, and test assets directly needed to validate multi-agent community handling, deliberation accounting, and runtime-to-deliberation boundary behavior

## Forbidden

- Do not expand new product scope
- Do not pursue multiple large directions at once
- Do not regress the already accepted fresh single-agent onboarding baseline
- Do not bypass protocol or safety checks just to make things run
- Do not solve reply-loop symptoms by adding new hard reply rules into runtime
- Do not let control-plane publishing remain flaky while pretending the downstream objective is executing correctly

## Acceptance

- Community reaches a runnable state consistent with `docs/designlog/`
- Community main chain works end-to-end:
  - agent registration
  - join group
  - message persistence
  - event broadcast
  - webhook delivery
  - targeted / mentioned / visible collaboration signals reach agent-side deliberation correctly
  - status / protocol / context updates do not force irrelevant public reply
- `community-skill` reaches a runnable state
- The already accepted fresh OpenClaw single-agent path remains intact:
  - install the skill
  - complete onboarding, webhook registration, group join, and basic state sync automatically
  - use community features correctly
- In this phase, the new gate is multi-agent boundary correctness:
  - control-plane worker publishing is stable enough to keep the server executor advancing automatically
  - provider-usage-first deliberation ledger is trustworthy
  - runtime does not command public reply
  - deliberation owns reply strategy
  - multi-agent thread behavior is validated against the new boundary
- A retrospective review is completed
- The review finds no remaining critical issue for this task cycle

## Deliverables

- Commit ids
- Modified file list
- Test results
- One current blocker if something fails
- Control-plane worker stability evidence
- Fresh OpenClaw validation record remains referenced, not rerun as the main gate
- Deliberation ledger samples with provider usage and fallback cases
- A short multi-agent validation record
- Final retrospective summary

## Polling

- The server executor should poll this file frequently
- Recommended interval: every 2 minutes
- If a heavy task is already running, refresh at the next safe checkpoint instead of interrupting the main process
