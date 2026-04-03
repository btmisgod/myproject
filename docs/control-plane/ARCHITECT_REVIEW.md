# ARCHITECT REVIEW

## Decision

- Continue

## Architecture Judgment

- The fresh single-agent acceptance phase is complete and should remain accepted.
- The new active problem is not onboarding. It is the live multi-agent community path:
  - deliberation token accounting is not yet trustworthy enough for cost analysis
  - runtime still carries reply-command semantics that are too heavy
  - `targeted` still behaves too much like a must-public-reply trigger
  - `message_type` is still heavier than the intended lightweight semantic role
- No rollback is needed for the already accepted onboarding and single-agent baseline fixes.
- The next phase should tighten boundaries instead of adding more runtime rules.
- Provider usage returned by the model service should be the primary accounting source because reading returned usage does not add prompt token cost.

## Accepted Results

- Server-verified runtime responsibility boundaries are accepted as the first baseline.
- Runtime refresh for already-onboarded workspaces is accepted.
- Profile sync as a soft dependency is accepted.
- JSON-safe message protocol serialization is accepted.
- Fresh-install onboarding, runtime installation, and first targeted execution recovery are accepted as current-phase progress.
- Fresh single-agent acceptance is accepted as phase-complete.

## Rejected / Out-of-Scope Changes

- No new feature expansion
- No task-platform rebuild
- No broad workflow or task-contract expansion in this phase
- No new hard reply rules added into runtime just to suppress loops
- No display-name-based `self_message` hacks
- No curl / sender-channel hardening in this phase unless it blocks the active objective directly

## Next Minimal Action

Start with the accounting and boundary foundation, not with a large loop-repair branch:

- keep the already accepted fresh single-agent acceptance record intact
- first repair deliberation accounting in `community-skill`
  - use provider-returned `usage` as the primary source
  - keep local module-level estimates only as fallback when provider usage is absent
  - distinguish explicit terminal states instead of mixing real calls and pending skeletons
- then reduce runtime semantics
  - runtime should extract responsibility signals and minimal semantic framing only
  - runtime should not act like a public-reply commander
  - `targeted` should mean strong processing signal that must enter deliberation, not a mechanical must-public-reply command
- keep reply-strategy decisions inside the deliberation module
- move `message_type` toward lightweight semantic use plus group-local extension, not stronger bottom-layer control
- after those code changes, run a short multi-agent validation window and record:
  - provider usage vs fallback ledger behavior
  - runtime output shape
  - deliberation outcome
  - whether the targeted thread still relays excessively

Do not reopen the already-completed onboarding gate as the main phase driver.

## Prompt Delta

The next server prompt should switch from fresh single-agent acceptance to multi-agent boundary repair with accounting first. It should instruct the server to:

- implement provider-usage-first deliberation accounting with explicit terminal states
- keep module-level token breakdown as local fallback only
- reduce runtime so it no longer commands public reply behavior
- move reply-strategy ownership into the deliberation module
- keep `message_type` lightweight
- validate these changes with a short controlled multi-agent interaction window and record the evidence
