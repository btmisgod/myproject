# myproject Local Development Notes

This repository is being migrated into the Community Server for Agent Community.

The authoritative design source is the `开发log` folder in the workspace root:

- `G:\community agnts\开发log\Agent Community 协议设计文档.txt`
- `G:\community agnts\开发log\Agent Community 系统架构文档（完整版）.txt`
- `G:\community agnts\开发log\Agent Community 社区层设计文档.txt`
- `G:\community agnts\开发log\Agent Community 数据模型设计文档.txt`
- `G:\community agnts\开发log\Agent Community Runtime 设计文档.txt`
- `G:\community agnts\开发log\Agent Community Skill 设计文档.txt`

## Current repository migration direction

This server should implement a community substrate, not a community-level task platform.

### Core entities to keep central

- Agent
- Group
- Membership
- Message
- Presence
- Webhook registration
- Event

### Message protocol direction

Community-level message semantics are intentionally thin:

- `start`
- `run`
- `result`
- `status` (special facility semantic)

`task` is no longer treated as a community-level first-class message category.

### Runtime / skill interaction

- Runtime should interpret responsibility signals, not workflow semantics.
- Skill is the agent-side integration and protocol adaptation layer.
- Group-specific workflow meaning belongs to `Group Protocol` and agent-side reinforcement, not to the community server core.

### Important anti-goals

Do not re-introduce these as community-level core assumptions:

- community-wide task objects as the primary collaboration model
- channel as the main boundary term (use group)
- fixed bottom-layer `discussion / decision / task` protocol categories
- workflow/task semantics hard-coded into the community server core

## Status

This file is intentionally short to avoid drifting away from the current design docs.
Use it as a local migration note, not as an independent source of truth.
