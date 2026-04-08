from datetime import datetime
import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.agents import AgentRead
from app.schemas.common import EventEnvelope
from app.schemas.groups import GroupRead
from app.schemas.messages import MessageRead
from app.schemas.presence import PresenceRead


class GroupProjectionSnapshot(BaseModel):
    group: GroupRead
    members: list[AgentRead]
    online_members: list[PresenceRead]
    latest_messages: list[MessageRead]
    latest_events: list[EventEnvelope]
    host_summary: dict[str, Any]
    replay_cursor: int | None
    projector: str = "web"


class PublishableProjection(BaseModel):
    event: EventEnvelope
    entity: dict[str, Any]
    projection_type: str = "group_event"
    version: int = 2
    group_id: uuid.UUID
    occurred_at: datetime | None = None
    delivery_scope: dict[str, Any] = Field(default_factory=dict)
    message: dict[str, Any] | None = None

