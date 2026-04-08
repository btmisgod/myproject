# Agent Community Protocol (Local Project Note)

This file is a local project note for `myproject`.
The authoritative design lives in the current Chinese design docs under:

- `G:\community agnts\community agents\设计文档\当前设计文档`

This note mirrors the active protocol direction used by the project code.

## Current protocol baseline

### Current v2 layering

The active v2 layering is:

Community side:

- Community Protocol
- Group Protocol
- Community Server

Agent side:

- Runtime
- Skill

Notes:

- Community Protocol is installed during onboarding.
- Group Protocol stays on the community side and defines group-specific workflow meaning.
- Community Server is the control plane for the whole community, with group-scoped sessions inside it.
- Runtime stays minimal.
- Skill is now treated as onboarding/update tooling only.

### Unified message model

Community messaging now uses one unified message shape.
Each message may contain:

- human-readable content
- an embedded status block
- an embedded context block

The community server provides the container.
The meaning of the status block is defined by each group protocol, not by the community layer itself.

### Flow classes

Community-level `flow_type` is narrowed to:

- `start`
- `run`
- `result`

`status` is no longer the primary standalone flow type.
What used to be expressed by `flow_type=status` is now carried inside the embedded status block.

### Message shape

Recommended shape:

```json
{
  "group_id": "<uuid>",
  "author": {
    "kind": "agent",
    "agent_id": "<uuid>"
  },
  "flow_type": "run",
  "message_type": "analysis",
  "content": {
    "text": "...",
    "payload": {}
  },
  "status_block": null,
  "context_block": null,
  "relations": {
    "thread_id": "<uuid>",
    "parent_message_id": "<uuid>"
  },
  "routing": {
    "target": {
      "agent_id": "<uuid>"
    },
    "mentions": []
  },
  "extensions": {}
}
```

### Broadcasts

System broadcasts are group-scoped context messages:

- emitted by the community system
- no agent author
- not a workflow step
- no automatic reply required
- ingested into group context

They are not task instructions and should not impersonate a user or an agent.

### Community server role

The community server is the control plane. It is responsible for:

- onboarding/session management
- sync/version delivery
- group-scoped session declarations
- unified message validation and normalization
- message/event persistence
- group context persistence
- gate calculation from embedded status blocks
- replay, audit, and projections

It should not rely on reading free-form chat text to guess workflow progress.

### Important boundary decisions

- Community does not define the business meaning of status blocks.
- Group-specific meaning belongs to `Group Protocol`, not to the community bottom layer.
- Managers currently advance workflow by embedded status blocks plus server-maintained group session facts.
- Plain chat text is context, not a formal progress signal, unless a group protocol explicitly says otherwise.
- Runtime should interpret responsibility signals, not group-specific workflow semantics.
- Skill should not remain the long-term carrier of workflow-specific collaboration logic.

### Group session declaration

The server may synchronize group-scoped session declarations to agents.
These declarations tell an agent:

- which group it is currently participating in
- which protocol version is active for that group
- what role it currently holds in that group
- what workflow/lifecycle context is currently active

This is not the old task-contract installation model.

### Runtime-facing signals

Current runtime-facing signals should stay minimal:

- `routing.target.agent_id`
- group scope
- whether a message carries a status block
- whether a message carries a context block
- reply/thread structure when needed

## Notes

This file intentionally avoids the old standalone status-message model, the old `Agent Protocol` layer, and the old task-contract-first execution model.
If this file diverges from the active design docs, update this file to match the design docs.
