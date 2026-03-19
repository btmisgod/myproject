import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import PresenceState
from app.schemas.common import ORMModel


class PresenceUpdateRequest(BaseModel):
    group_id: uuid.UUID
    state: PresenceState
    note: str | None = Field(default=None, max_length=255)


class PresenceRead(ORMModel):
    id: uuid.UUID
    group_id: uuid.UUID
    agent_id: uuid.UUID
    state: str
    note: str | None
    created_at: datetime
    updated_at: datetime

