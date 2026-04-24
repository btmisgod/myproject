from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AgentSessionSyncRequest(BaseModel):
    agent_id: uuid.UUID | None = None
    agent_session_id: str | None = None
    community_protocol_version: str | None = None
    runtime_version: str | None = None
    skill_version: str | None = None
    onboarding_version: str | None = None
    group_session_versions: dict[str, str] = Field(default_factory=dict)
    group_context_versions: dict[str, str] = Field(default_factory=dict)
    full_sync_requested: bool = False


class GroupSessionDeclaration(BaseModel):
    group_id: uuid.UUID
    group_session_id: str
    group_session_version: str
    protocol_version: str
    workflow_id: str
    current_mode: str
    current_stage: str
    group_context_version: str
    gate_snapshot: dict[str, object] = Field(default_factory=dict)
    manager_agent_ids: list[str] = Field(default_factory=list)
    manager_control_turn: dict[str, object] = Field(default_factory=dict)


class GroupContextUpdate(BaseModel):
    group_id: uuid.UUID
    group_context_version: str
    group_context: dict[str, object] = Field(default_factory=dict)


class AgentSessionView(BaseModel):
    agent_id: uuid.UUID
    agent_session_id: str
    community_protocol_version: str
    runtime_version: str | None = None
    skill_version: str | None = None
    onboarding_version: str | None = None
    last_sync_at: datetime
    state: str = "active"


class AgentSessionSyncResponse(BaseModel):
    community_protocol_version: str
    onboarding_required: bool = False
    sync_mode: str
    agent_session: AgentSessionView
    group_session_declarations: list[GroupSessionDeclaration] = Field(default_factory=list)
    removed_groups: list[str] = Field(default_factory=list)
    group_context_updates: list[GroupContextUpdate] = Field(default_factory=list)
    pending_broadcasts: list[dict[str, object]] = Field(default_factory=list)
