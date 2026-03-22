# GitHub Control Plane

This directory is the shared control surface for the local architect Codex and the server execution Codex.

The goal is not direct model-to-model chat. The goal is a stable repo-based workflow:

- The architect side defines the current single objective, constraints, acceptance, and next step.
- The server side executes only the current objective and reports evidence, logs, tests, and a single blocker.
- Both sides use repository documents as the only shared context.

When repo URLs, branches, or key paths are needed, use [REPO_INDEX.md](./REPO_INDEX.md) as the canonical source.

## Files

- [CONTROL.md](./CONTROL.md)
  Current long-range objective, current active objective, forbidden actions, acceptance, and deliverables.
- [SERVER_REPORT.md](./SERVER_REPORT.md)
  Server execution report with logs, tests, blocker, and next minimal suggestion.
- [ARCHITECT_REVIEW.md](./ARCHITECT_REVIEW.md)
  Architect judgment, accepted results, rejected scope, and next minimal action.
- [OPERATING_RULES.md](./OPERATING_RULES.md)
  Shared operating rules for both Codex agents.
- [SERVER_EXEC_PROMPT.md](./SERVER_EXEC_PROMPT.md)
  Standard prompt template for the server execution Codex.
- [ARCHITECT_REVIEW_PROMPT.md](./ARCHITECT_REVIEW_PROMPT.md)
  Standard prompt template for the architect/review Codex.

## Workflow

1. The architect updates [CONTROL.md](./CONTROL.md).
2. The server reads `CONTROL.md`, `OPERATING_RULES.md`, and `docs/designlog/`.
3. The server executes and updates [SERVER_REPORT.md](./SERVER_REPORT.md).
4. The architect reads `CONTROL.md`, `SERVER_REPORT.md`, and `docs/designlog/`.
5. The architect updates [ARCHITECT_REVIEW.md](./ARCHITECT_REVIEW.md) and defines the next minimal action.

## High-Frequency Collaboration

This control plane supports high-frequency polling plus direct user instructions:

- The user can continue giving instructions in the main chat.
- The architect Codex must first sync those instructions into the GitHub control-plane docs.
- The server execution side does not act on chat logs directly. It acts on repo docs only.
- Both sides should poll frequently enough to keep momentum without interrupting heavy tasks.

Recommended cadence:

- Server side: every 2 minutes read `CONTROL.md`
- Architect side: every 2 minutes read `SERVER_REPORT.md`

If a heavy task is in progress:

- Do not interrupt the main process aggressively.
- Refresh control docs at the next safe checkpoint.

## Core Principles

- Only one current active objective at a time
- The server side does not expand scope on its own
- The architect side does not ask the server to pursue multiple high-risk branches in parallel
- Every important conclusion should include commit ids, file paths, logs, or test evidence
- Design docs remain the highest source of truth over ad hoc runtime guesses
