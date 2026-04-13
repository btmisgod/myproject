import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentSessionSyncRequest(BaseModel):
    agent_id: uuid.UUID | None = None
    agent_session_id: uuid.UUID | None = None
    community_protocol_version: str | None = None
    runtime_version: str | None = None
    skill_version: str | None = None
    onboarding_version: str | None = None
    group_session_versions: dict[str, str] = Field(default_factory=dict)
    group_context_versions: dict[str, str] = Field(default_factory=dict)
    full_sync_requested: bool = False


class AgentSessionRead(BaseModel):
    agent_session_id: uuid.UUID
    agent_id: uuid.UUID
    community_protocol_version: str
    runtime_version: str
    skill_version: str
    onboarding_version: str
    last_sync_at: datetime


class GroupSessionDeclaration(BaseModel):
    group_id: uuid.UUID
    group_session_id: uuid.UUID
    group_session_version: str
    group: dict[str, Any]
    group_protocol: dict[str, Any]


class GroupContextUpdate(BaseModel):
    group_id: uuid.UUID
    group_context_version: str
    group_context: dict[str, Any]


class AgentSessionSyncResponse(BaseModel):
    community_protocol_version: str
    onboarding_required: bool
    agent_session: AgentSessionRead
    group_session_declarations: list[GroupSessionDeclaration] = Field(default_factory=list)
    group_context_updates: list[GroupContextUpdate] = Field(default_factory=list)
    removed_groups: list[str] = Field(default_factory=list)
