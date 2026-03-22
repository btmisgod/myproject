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
- The first fresh-instance blocker is now specific and actionable: fresh-install `targeted run` is being classified as `observe_only` instead of `execute + reply`.

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

Diagnose and fix the fresh-install runtime boundary mismatch only:

- determine why fresh-install `targeted run` is being classified as `observe_only`
- compare the fresh instance runtime path, installed asset, and context extraction path against the already-verified instance
- apply the smallest fix that restores fresh-instance baseline behavior:
  - targeted run => execute + reply

Do not reopen unrelated baseline checks unless they are needed to prove this fix.

## Prompt Delta

The next server prompt should focus only on the fresh-instance targeted-runtime mismatch. It should instruct the server to compare the fresh instance against the already-verified instance, find the first divergence, fix it with the smallest possible change, and rerun fresh targeted validation.
