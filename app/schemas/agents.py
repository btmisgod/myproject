import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class AgentProfile(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    handle: str | None = Field(default=None, max_length=40)
    identity: str | None = Field(default=None, max_length=80)
    tagline: str | None = Field(default=None, max_length=160)
    bio: str | None = Field(default=None, max_length=500)
    avatar_text: str | None = Field(default=None, max_length=8)
    accent_color: str | None = Field(default=None, max_length=20)
    expertise: list[str] = Field(default_factory=list, max_length=12)
    home_group_slug: str | None = Field(default=None, max_length=120)


class AgentCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class AgentRead(ORMModel):
    id: uuid.UUID
    name: str
    description: str | None
    metadata_json: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AgentRegistrationResult(BaseModel):
    agent: AgentRead
    token: str


class AgentLoginRequest(BaseModel):
    token: str


class AgentProfileUpdateRequest(BaseModel):
    profile: AgentProfile
