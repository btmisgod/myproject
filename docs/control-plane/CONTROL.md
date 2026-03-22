# CONTROL

## Long-Range Objective

Complete the Community project according to the design docs and run it successfully.
Complete the `community-skill` project so that installing it on a fresh OpenClaw instance automatically connects that agent to the community and lets it use community features correctly.
After both are complete, run a retrospective review. If the review is clean, end this task cycle.

## Current Active Objective

Validate the fresh OpenClaw installation path and confirm that a newly installed `community-skill` instance can complete automatic onboarding and use the community baseline correctly in a single-agent acceptance path. Do not treat reciprocal multi-agent reply-loop behavior as a gating blocker in this phase.

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
- Deployment scripts, env templates, service configs, and test assets directly needed to validate fresh OpenClaw auto-onboarding

## Forbidden

- Do not expand new product scope
- Do not pursue multiple large directions at once
- Do not skip the agreed validation chain
- Do not bypass protocol or safety checks just to make things run

## Acceptance

- Community reaches a runnable state consistent with `docs/designlog/`
- Community main chain works end-to-end:
  - agent registration
  - join group
  - message persistence
  - event broadcast
  - webhook delivery
  - targeted run => execute + reply
  - non-targeted run => observe_only / no outbound / no reply
  - status => enters system but agent does not auto-reply
- `community-skill` reaches a runnable state
- A fresh OpenClaw instance can:
  - install the skill
  - complete onboarding, webhook registration, group join, and basic state sync automatically
  - use community features correctly
- A retrospective review is completed
- The review finds no remaining critical issue for this task cycle

## Deliverables

- Commit ids
- Modified file list
- Test results
- One current blocker if something fails
- Fresh OpenClaw validation record
- Final retrospective summary

## Polling

- The server executor should poll this file frequently
- Recommended interval: every 2 minutes
- If a heavy task is already running, refresh at the next safe checkpoint instead of interrupting the main process
