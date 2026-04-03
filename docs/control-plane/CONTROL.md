# CONTROL

## Long-Range Objective

Complete the Community project according to the design docs and run it successfully.
Complete the `community-skill` project so that installing it on a fresh OpenClaw instance automatically connects that agent to the community and lets it use community features correctly.
After both are complete, run a retrospective review. If the review is clean, end this task cycle.

## Current Active Objective

Repair the live multi-agent `community-skill` communication boundary while preserving correct fresh skill onboarding.

The only active objective in this loop is:

- keep the already accepted provider-usage-first deliberation ledger behavior intact
- reduce runtime so it only extracts responsibility signals and minimal semantic framing
- remove any remaining mechanical must-public-reply semantics from runtime and bottom-layer handling
- move public reply / no-reply / closure decisions into deliberation
- keep `message_type` lightweight and stop treating it like a heavy control enum
- reduce targeted-thread relay, self-reply, and confirmation-loop behavior by fixing boundaries rather than by ad hoc hard rules
- preserve the already accepted fresh single-agent onboarding baseline and confirm the current install path still connects a fresh skill instance correctly

## Instruction Source

Priority order:

1. The latest user instruction in the main architect chat
2. The current staged objective contract in `OBJECTIVE.md`
3. This file: `CONTROL.md`
4. The latest minimal action in `ARCHITECT_REVIEW.md`

Rules:

- User chat instructions do not go directly to the server executor.
- The architect Codex must first sync them into the GitHub control-plane docs.
- The server executor trusts repo docs, not chat logs.
- The server executor should read `OBJECTIVE.md` and `CONTROL.md` together before deciding whether the active objective changed.

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
- Do not reopen control-plane redesign unless it becomes the single blocker again

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
  - fresh skill onboarding still works correctly after the boundary changes
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
- Fresh skill install / onboarding preservation evidence
- Final retrospective summary

## Polling

- The server executor should poll this file frequently
- Recommended interval: every 2 minutes
- If a heavy task is already running, refresh at the next safe checkpoint instead of interrupting the main process
