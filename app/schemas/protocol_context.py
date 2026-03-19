import uuid
from typing import Any

from pydantic import BaseModel, Field


class ProtocolContextRequest(BaseModel):
    # Agent-facing request shape for fetching scoped protocol context from community.
    # The caller does not provide agent_id directly; community resolves it from auth.
    group_id: uuid.UUID
    action_type: str = Field(min_length=2, max_length=80)
    trigger: str | None = Field(default=None, max_length=80)
    resource_id: uuid.UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
