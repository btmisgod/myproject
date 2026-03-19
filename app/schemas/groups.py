import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import GroupType
from app.schemas.common import ORMModel


class GroupCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    slug: str = Field(min_length=3, max_length=120, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(default=None, max_length=500)
    group_type: GroupType
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class GroupRead(ORMModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    group_type: str
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class JoinGroupRequest(BaseModel):
    role: str = Field(default="member", max_length=50)


class MembershipRead(ORMModel):
    id: uuid.UUID
    group_id: uuid.UUID
    agent_id: uuid.UUID
    role: str
    created_at: datetime
    updated_at: datetime

