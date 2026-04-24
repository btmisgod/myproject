from enum import StrEnum


class GroupType(StrEnum):
    PUBLIC_LOBBY = "public_lobby"
    PROJECT = "project"
    FUNCTIONAL = "functional"


class TaskStatus(StrEnum):
    # Internal persistence states for the current group-scoped collaboration
    # object helper. These are not community-level public protocol semantics.
    PENDING = "pending"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


class PresenceState(StrEnum):
    ONLINE = "online"
    IDLE = "idle"
    OFFLINE = "offline"


class FlowType(StrEnum):
    START = "start"
    RUN = "run"
    RESULT = "result"
    # Deprecated compatibility alias only. The formal primary model is
    # start/run/result with embedded status_block.
    STATUS = "status"


class MessageType(StrEnum):
    # Example fine-grained semantics used by current server-side helpers.
    # These should not be treated as community-bottom-layer fixed standards.
    PROPOSAL = "proposal"
    ANALYSIS = "analysis"
    QUESTION = "question"
    CLAIM = "claim"
    PROGRESS = "progress"
    HANDOFF = "handoff"
    REVIEW = "review"
    DECISION = "decision"
    SUMMARY = "summary"
    META = "meta"


class EventType(StrEnum):
    AGENT_REGISTERED = "agent.registered"
    GROUP_CREATED = "group.created"
    GROUP_JOINED = "group.joined"
    MESSAGE_POSTED = "message.posted"
    GROUP_SESSION_UPDATED = "group_session.updated"
    BROADCAST_DELIVERED = "broadcast.delivered"
    # Internal group-scoped collaboration object events retained for current
    # server compatibility. They are not evidence of a community-level task
    # platform model.
    TASK_CREATED = "task.created"
    TASK_CLAIMED = "task.claimed"
    TASK_UPDATED = "task.updated"
    TASK_HANDOFF = "task.handoff"
    PRESENCE_UPDATED = "presence.updated"

