import uuid
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.common import ORMModel


class WebhookSubscriptionCreate(BaseModel):
    target_url: HttpUrl
    secret: str = Field(min_length=12, max_length=128)
    description: str | None = Field(default=None, max_length=255)


class WebhookSubscriptionRead(ORMModel):
    id: uuid.UUID
    group_id: uuid.UUID
    target_url: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AgentWebhookSubscriptionRead(ORMModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    target_url: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
