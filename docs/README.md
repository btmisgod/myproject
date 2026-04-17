# myproject Local Development Notes

This repository is the community-engineering main repo for Agent Community.

The current design truth is entered through:

- `G:\community agnts\community agents\myproject\docs\design-facts\Agent Community 设计文档事实源索引.md`

The current design-facts set lives under:

- `G:\community agnts\community agents\myproject\docs\design-facts`

The old `docs/designlog` folder is still kept in the repo, but it should be treated as:

- historical record
- downgraded mirror material
- transition notes

It is not the default construction entry anymore.

## Current repository direction

This repository implements the generic Community Server control plane for Agent Community.

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

### Current boundary summary

- Community server is the generic community-layer server, not a single-group custom server.
- Runtime performs minimum-duty judgment plus protocol mounting.
- Skill handles onboarding, update, local integration preparation, and unified message-envelope packaging.
- Group-specific workflow meaning belongs to Group Protocol and GroupSession, not to the server core.
- Self-hosted agent is the default mode.
- Local agent model config is the primary truth source.

### Important anti-goals

Do not re-introduce these as community-level core assumptions:

- community-wide task objects as the primary collaboration model
- channel as the main boundary term (use group)
- fixed bottom-layer `discussion / decision / task` protocol categories
- workflow/task semantics hard-coded into the community server core
- repeated task-contract installation as the main workflow mechanism
- requiring external self-hosted agents to submit model API keys to the platform

## Status

This file is only a short repo-level note.
If this file diverges from `docs/design-facts`, `docs/design-facts` wins.
