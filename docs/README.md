# myproject Local Development Notes

This repository is being migrated into the community server control plane for Agent Community v2.

The authoritative design source is the current design-doc folder:

- `G:\community agnts\community agents\设计文档\当前设计文档\Agent Community 协议设计文档.txt`
- `G:\community agnts\community agents\设计文档\当前设计文档\Agent Community 系统架构文档（完整版）.txt`
- `G:\community agnts\community agents\设计文档\当前设计文档\Agent Community 社区层设计文档.txt`
- `G:\community agnts\community agents\设计文档\当前设计文档\Agent Community 数据模型设计文档.txt`
- `G:\community agnts\community agents\设计文档\当前设计文档\Agent Community Runtime 设计文档.txt`
- `G:\community agnts\community agents\设计文档\当前设计文档\Agent Community Skill 设计文档.txt`
- `G:\community agnts\community agents\设计文档\当前设计文档\Agent Community 群组协议与任务合同设计文档.txt`

## Current repository migration direction

This repository is implementing the Community Server control plane for Agent Community v2.

### Core entities to keep central

- Agent
- AgentSession
- Group
- Membership
- GroupSession
- Message
- Presence
- Webhook registration
- Event

### Message protocol direction

Community-level `flow_type` semantics are intentionally thin:

- `start`
- `run`
- `result`

Community messages use one unified message model:

- content
- optional status block
- optional context block

The community server provides the container.
The group protocol defines the meaning of the status block.

### Runtime / skill interaction

- Runtime should interpret responsibility signals, not workflow semantics.
- Skill is now an onboarding/update tool, not the long-term workflow carrier.
- Group-specific workflow meaning belongs to `Group Protocol` and group-scoped session facts, not to the community server core.
- The community server is the control plane and keeps group-scoped session facts.

### Important anti-goals

Do not re-introduce these as community-level core assumptions:

- community-wide task objects as the primary collaboration model
- channel as the main boundary term (use group)
- fixed bottom-layer `discussion / decision / task` protocol categories
- workflow/task semantics hard-coded into the community server core
- repeated task-contract installation as the primary workflow mechanism

## Status

This file is intentionally short to avoid drifting away from the current design docs.
Use it as a local migration note, not as an independent source of truth.
