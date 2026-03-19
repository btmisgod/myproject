import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PaginationMeta(BaseModel):
    limit: int
    offset: int
    count: int


class EventEnvelope(ORMModel):
    sequence_id: int
    event_id: uuid.UUID
    group_id: uuid.UUID
    event_type: str
    aggregate_type: str
    aggregate_id: uuid.UUID | None
    actor_agent_id: uuid.UUID | None
    payload: dict[str, Any]
    created_at: datetime
