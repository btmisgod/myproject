# Active Objective Contract

## Purpose

This file is the lightweight, user-facing contract for the current staged long-running task.

Use it when the architect wants to set or replace the current staged objective without manually
rewriting the full control-plane docs.

## Current Objective

### Title

Deliver stable multi-agent community communication and correct fresh skill onboarding.

### Outcome

The current staged business outcome is:

- agents can communicate in the community without relay loops, self-reply bugs, or runtime-forced reply mistakes
- `community-skill` can still connect a fresh OpenClaw agent into the community correctly after install
- the next step after this stage is group-task testing on top of a stable communication baseline

### Current Stage

Community communication boundary repair and onboarding preservation.

### Scope

- `community-skill` runtime / deliberation / onboarding path
- minimal `myproject` changes only if the current communication path cannot be validated without them
- multi-agent validation in the current community environment

### Acceptance

- deliberation token accounting remains provider-usage-first and trustworthy
- runtime no longer commands public public-reply behavior
- `targeted` is treated as a strong processing signal, not a mechanical must-public-reply trigger
- reply strategy and closure behavior are owned by deliberation
- `message_type` is lightweight and no longer acts like a heavy control field
- a short multi-agent validation shows agents can communicate without runaway relay/self-reply bugs
- the already accepted fresh single-agent onboarding path remains intact and a fresh skill install can still connect correctly

### Constraints

- keep exactly one active staged objective
- preserve the already accepted single-agent onboarding baseline
- do not reopen control-plane redesign unless it becomes the single blocker again

### Notes For The Local Controller

- prefer updating `ARCHITECT_REVIEW.md` before rewriting `CONTROL.md`
- only update `CONTROL.md` when the current active objective summary itself must change
- treat this file as the highest-priority staged objective input after direct user chat instructions
