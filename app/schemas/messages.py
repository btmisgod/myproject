import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import MessageType
from app.schemas.common import ORMModel


class MessageCreate(BaseModel):
    group_id: uuid.UUID
    parent_message_id: uuid.UUID | None = None
    thread_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None
    message_type: MessageType
    content: dict[str, Any] = Field(default_factory=dict)


class MessageRead(ORMModel):
    id: uuid.UUID
    group_id: uuid.UUID
    agent_id: uuid.UUID | None
    task_id: uuid.UUID | None
    parent_message_id: uuid.UUID | None
    thread_id: uuid.UUID | None
    message_type: str
    content: dict[str, Any]
    created_at: datetime
    updated_at: datetime

