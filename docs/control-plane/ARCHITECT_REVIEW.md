# ARCHITECT REVIEW

## Decision

- Continue

## Architecture Judgment

- The current server-verified baseline is aligned with the design docs:
  - targeted run => execute + reply
  - non-targeted run => observe_only / no outbound / no reply
  - status => enters system / no auto reply
- Community and skill now share the same first-baseline behavior model.
- No rollback is needed for the verified active-chain fixes.
- Autopilot is active on the server and has already completed one fresh-instance validation loop.
- The fresh-install `targeted run` mismatch has been cleared on the server side.
- The new fresh-instance blocker is more concrete: the fresh instance now executes and replies, but then enters a reciprocal auto-reply loop.

## Accepted Results

- Server-verified runtime responsibility boundaries are accepted as the first baseline.
- Runtime refresh for already-onboarded workspaces is accepted.
- Profile sync as a soft dependency is accepted.
- JSON-safe message protocol serialization is accepted.

## Rejected / Out-of-Scope Changes

- No new feature expansion
- No task-platform rebuild
- No broad workflow or task-contract expansion in this phase

## Next Minimal Action

Diagnose and cut the reciprocal auto-reply loop on the fresh instance only:

- identify why the fresh instance replies correctly to a targeted run but then keeps responding to the follow-up message stream
- compare the reply classification and self/peer message handling path between the fresh instance and the already-verified instance
- apply the smallest fix that preserves:
  - targeted run => execute + reply
  - non-targeted run => observe_only / no outbound / no reply

Do not reopen unrelated install/bootstrap work unless it is required to prove this fix.

## Prompt Delta

The next server prompt should focus only on the fresh-instance reciprocal auto-reply loop. It should instruct the server to preserve the corrected targeted behavior, find the first reply-loop divergence, stop the loop with the smallest possible change, and rerun fresh targeted plus non-targeted validation.
