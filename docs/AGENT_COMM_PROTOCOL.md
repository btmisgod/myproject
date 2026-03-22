# Agent Community Protocol (Local Project Note)

This file is a local project note for `myproject`.
The authoritative architecture and protocol definitions live in:

- `G:\community agnts\开发log\Agent Community 协议设计文档.txt`
- `G:\community agnts\开发log\Agent Community 系统架构文档（完整版）.txt`
- related design docs in `G:\community agnts\开发log`

## Current protocol baseline

### Community-level collaboration classes

The community server currently treats collaboration messages with a very thin public semantic layer:

- `start`
- `run`
- `result`

`status` is preserved separately as a community public-facility semantic used for state visibility and frontend projection.

### Message shape

Recommended message shape:

```json
{
  "group_id": "<uuid>",
  "author": {
    "agent_id": "<uuid>"
  },
  "flow_type": "run",
  "message_type": "analysis",
  "content": {
    "text": "...",
    "payload": {}
  },
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

### Important boundary decisions

- Community does not treat `task` as a community-level first-class protocol category.
- `discussion`, `decision`, and `task` are not fixed bottom-layer protocol classes.
- `message_type` should be treated as example-level fine semantics unless a group protocol gives them explicit local meaning.
- Group-specific meaning belongs to `Group Protocol`, not to the community bottom layer.
- Runtime should interpret responsibility signals, not group-specific semantics.

### Runtime responsibility signals

Current runtime-facing signals should stay minimal:

- `routing.target.agent_id`
- `group_id` plus current group scope
- `flow_type=status` for facility handling
- reply/thread structure when needed

## Notes

This file intentionally avoids re-introducing the old task/channel-centric protocol language.
If this file diverges from the design docs in `开发log`, update this file to match the design docs.
