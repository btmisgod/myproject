# CONTROL

## Long-Range Objective

Complete the Community project according to the design docs and run it successfully.
Complete the `community-skill` project so that installing it on a fresh OpenClaw instance automatically connects that agent to the community and lets it use community features correctly.
After both are complete, run a retrospective review. If the review is clean, end this task cycle.

## Current Active Objective

Stabilize the real multi-agent community path after the fresh single-agent acceptance phase. The next phase is to repair `community-skill` so that:

- deliberation token accounting is trustworthy and provider-usage-first
- runtime no longer commands public reply behavior
- reply strategy is owned by the deliberation module
- `message_type` stays a light semantic field instead of a heavy control enum
- reciprocal multi-agent thread relay / auto-reply behavior is reduced by boundary fixes rather than by ad hoc hard rules

Phase success rule for this stage:

- `community-skill` records deliberation cost with provider usage when available and with explicit fallback estimation only when provider usage is absent
- the ledger distinguishes real provider-returned calls from in-flight / failed / send-failed attempts with clear terminal states
- runtime is reduced to responsibility-signal extraction and minimal semantic framing, and no longer acts like a public-reply commander
- `targeted` is treated as a strong processing signal that must enter deliberation, not as a mechanical must-public-reply command
- the current implementation direction for `message_type` is aligned toward lightweight semantics plus group-local extension, not stronger bottom-layer control
- the server records concrete validation evidence from a short multi-agent interaction window after these changes

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
- `community-skill` code and docs related to onboarding, webhook, runtime, protocol adaptation, agent-side asset install, and automatic connection
- Deployment scripts, env templates, service configs, and test assets directly needed to validate multi-agent community handling, deliberation accounting, and runtime-to-deliberation boundary behavior

## Forbidden

- Do not expand new product scope
- Do not pursue multiple large directions at once
- Do not regress the already accepted fresh single-agent onboarding baseline
- Do not bypass protocol or safety checks just to make things run
- Do not solve reply-loop symptoms by adding new hard reply rules into runtime

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
- Fresh OpenClaw validation record remains referenced, not rerun as the main gate
- Deliberation ledger samples with provider usage and fallback cases
- A short multi-agent validation record
- Final retrospective summary

## Polling

- The server executor should poll this file frequently
- Recommended interval: every 2 minutes
- If a heavy task is already running, refresh at the next safe checkpoint instead of interrupting the main process
