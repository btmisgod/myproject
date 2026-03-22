import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import TaskStatus
from app.schemas.common import ORMModel


class TaskCreate(BaseModel):
    # Internal request shape for the current group-scoped collaboration object
    # helper. This schema is not a community-level public task model contract.
    group_id: uuid.UUID
    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    parent_task_id: uuid.UUID | None = None


class TaskRead(ORMModel):
    # Compatibility read model for persisted group-scoped collaboration objects.
    id: uuid.UUID
    group_id: uuid.UUID
    title: str
    description: str | None
    status: str
    claimed_by_agent_id: uuid.UUID | None
    parent_task_id: uuid.UUID | None
    metadata_json: dict[str, Any]
    result_summary: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class TaskClaimRequest(BaseModel):
    note: str | None = Field(default=None, max_length=300)


class TaskStatusUpdateRequest(BaseModel):
    status: TaskStatus
    note: str | None = Field(default=None, max_length=300)


class TaskHandoffRequest(BaseModel):
    target_agent_id: uuid.UUID | None = None
    summary: dict[str, Any] = Field(default_factory=dict)


class TaskResultSummaryRequest(BaseModel):
    summary: dict[str, Any] = Field(default_factory=dict)

