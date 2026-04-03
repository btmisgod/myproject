# ARCHITECT REVIEW

## Decision

- Continue

## Architecture Judgment

- The fresh single-agent acceptance phase is complete and should remain accepted.
- The server-side long-running worker is now stable enough to continue downstream work.
- Provider-usage-first deliberation accounting has been completed and should now be treated as accepted baseline for this phase.
- The new active problem is not onboarding. It is the live multi-agent community path:
  - runtime still carries reply-command semantics that are too heavy
  - `targeted` still behaves too much like a must-public-reply trigger
  - `message_type` is still heavier than the intended lightweight semantic role
  - targeted threads can still relay or loop across multiple agents
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
- Provider-usage-first deliberation ledger with explicit terminal states is accepted as phase-complete.

## Rejected / Out-of-Scope Changes

- No new feature expansion
- No task-platform rebuild
- No broad workflow or task-contract expansion in this phase
- No new hard reply rules added into runtime just to suppress loops
- No display-name-based `self_message` hacks
- No curl / sender-channel hardening in this phase unless it blocks the active objective directly
- No pretending that server execution is healthy if control-plane publishing is still racing remote `main`

## Next Minimal Action

Execute this in order:

1. Continue the active `community-skill` boundary repair branch.
   - keep the accepted ledger behavior intact
   - reduce runtime to responsibility-signal extraction and minimal semantic framing only
   - remove any remaining must-public-reply semantics from runtime and bottom-layer handling
   - treat `targeted` as a strong processing signal that must enter deliberation, not a mechanical reply command
   - keep reply strategy and closure behavior inside deliberation
   - move `message_type` toward lightweight semantic use plus group-local extension, not stronger bottom-layer control
2. After those code changes, run a short multi-agent validation window and record:
   - runtime output shape
   - deliberation outcome
   - whether targeted threads still relay excessively
   - whether self-reply / confirmation-loop behavior is gone or materially reduced
3. Then do one focused preservation check on fresh skill onboarding:
   - confirm a fresh install still connects the skill to the community correctly
   - do not reopen onboarding redesign unless this preservation check fails

Do not reopen the already-completed onboarding gate as the main phase driver.

## Prompt Delta

The next server prompt should continue the now-active business branch. It should instruct the server to:

- preserve the already accepted provider-usage-first ledger behavior
- reduce runtime so it no longer commands public reply behavior
- move reply-strategy ownership into the deliberation module
- change `targeted` from a mechanical reply trigger into a strong processing signal that enters deliberation
- keep `message_type` lightweight
- validate the new boundary with a short controlled multi-agent interaction window
- then run one focused preservation check to ensure fresh skill onboarding still connects correctly
