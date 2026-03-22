# Operating Rules

## Shared Rules

1. `docs/designlog/` is the highest source of truth.
2. The server executor solves only the current active objective and does not expand scope on its own.
3. The architect side defines only one current active objective at a time.
4. Fix active-chain issues before cleaning dead or dormant code.
5. Every important conclusion must include evidence:
   - commit id
   - file path
   - logs
   - test command and result
6. User instructions from the main chat must be synced into control-plane docs by the architect Codex before the server acts on them.
7. The server executor does not consume chat logs directly. It consumes GitHub control-plane docs.
8. Poll frequently enough to maintain continuity, but do not interrupt a heavy in-flight process aggressively.

## Server Codex Rules

- Prefer the smallest possible fix
- Fix the active chain before running regression
- Do not perform broad refactors without control-plane approval
- If something fails, report exactly one current blocker
- Poll `CONTROL.md` every 2 minutes by default
- If a heavy command or test is running, refresh at the next safe checkpoint
- If `CONTROL.md` did not change, continue the current objective rather than switching direction

## Architect Codex Rules

- Judge work first by design-doc alignment
- Do not promote temporary hotfix wording into official architecture
- Do not open multiple product or architecture directions at once
- Give the server exactly one next minimal action
- Poll `SERVER_REPORT.md` every 2 minutes by default
- Sync new user instructions into `CONTROL.md` or `ARCHITECT_REVIEW.md` quickly
- If the user changes the objective in chat, update the control plane immediately and treat the latest user instruction as canonical
