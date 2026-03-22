# Repository Index

This file is the canonical repository index for the GitHub control plane.
All humans and all Codex agents should prefer this file over ad hoc chat mentions when they need repo URLs, branches, or key control-plane paths.

## Canonical Repositories

- `myproject`
  - GitHub: [https://github.com/btmisgod/myproject](https://github.com/btmisgod/myproject)
  - Default branch: `main`
  - Control-plane root: `docs/control-plane/`
  - Design docs root: `docs/designlog/`

- `community-skill`
  - GitHub: [https://github.com/btmisgod/community-skill](https://github.com/btmisgod/community-skill)
  - Default branch: `main`

## Canonical Working Rules

1. The server executor should confirm it has pulled `main` from both repositories before starting work.
2. The official control plane lives only in `myproject/docs/control-plane/`.
3. Skill code changes happen in `community-skill`, but scope and priority are still defined by `myproject/docs/control-plane/CONTROL.md`.

## Current Control Files

- `docs/control-plane/CONTROL.md`
- `docs/control-plane/SERVER_REPORT.md`
- `docs/control-plane/ARCHITECT_REVIEW.md`
- `docs/control-plane/OPERATING_RULES.md`
- `docs/control-plane/SERVER_EXEC_PROMPT.md`
- `docs/control-plane/ARCHITECT_REVIEW_PROMPT.md`
