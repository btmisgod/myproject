from enum import StrEnum


class GroupType(StrEnum):
    PUBLIC_LOBBY = "public_lobby"
    PROJECT = "project"
    FUNCTIONAL = "functional"


class TaskStatus(StrEnum):
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


class MessageType(StrEnum):
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
    TASK_CREATED = "task.created"
    TASK_CLAIMED = "task.claimed"
    TASK_UPDATED = "task.updated"
    TASK_HANDOFF = "task.handoff"
    PRESENCE_UPDATED = "presence.updated"

