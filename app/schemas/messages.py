import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.common import ORMModel
from app.models.enums import FlowType
from app.services.message_protocol_mapper import normalize_message_to_canonical_v2, serialize_message_v2


class MessageAuthor(BaseModel):
    agent_id: uuid.UUID | None = None


class MessageRelations(BaseModel):
    thread_id: uuid.UUID | None = None
    parent_message_id: uuid.UUID | None = None


class MessageContent(BaseModel):
    text: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    blocks: list[Any] = Field(default_factory=list)
    attachments: list[Any] = Field(default_factory=list)


class MessageRoutingTarget(BaseModel):
    agent_id: str | None = None


class MessageRouting(BaseModel):
    target: MessageRoutingTarget = Field(default_factory=MessageRoutingTarget)
    mentions: list[Any] = Field(default_factory=list)


class MessageCreate(BaseModel):
    group_id: uuid.UUID
    author: MessageAuthor = Field(default_factory=MessageAuthor)
    author_kind: str | None = None
    flow_type: str
    message_type: str | None = None
    content: MessageContent = Field(default_factory=MessageContent)
    status_block: dict[str, Any] = Field(default_factory=dict)
    context_block: dict[str, Any] = Field(default_factory=dict)
    relations: MessageRelations = Field(default_factory=MessageRelations)
    routing: MessageRouting = Field(default_factory=MessageRouting)
    extensions: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _normalize_input(cls, value: Any) -> Any:
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return normalize_message_to_canonical_v2(value)
        return value

    @field_validator("flow_type")
    @classmethod
    def _validate_flow_type(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        allowed = {item.value for item in FlowType}
        if normalized not in allowed:
            raise ValueError(f"flow_type must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @property
    def agent_id(self) -> uuid.UUID | None:
        return self.author.agent_id

    @property
    def parent_message_id(self) -> uuid.UUID | None:
        return self.relations.parent_message_id

    @property
    def thread_id(self) -> uuid.UUID | None:
        return self.relations.thread_id


class MessageRead(ORMModel):
    id: uuid.UUID
    group_id: uuid.UUID
    author: MessageAuthor
    author_kind: str | None = None
    flow_type: str
    message_type: str | None = None
    content: MessageContent
    status_block: dict[str, Any] = Field(default_factory=dict)
    context_block: dict[str, Any] = Field(default_factory=dict)
    relations: MessageRelations
    routing: MessageRouting
    extensions: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def _normalize_output(cls, value: Any) -> Any:
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            if "group_id" in value and "flow_type" in value and "content" in value:
                return value
            return normalize_message_to_canonical_v2(value)
        return serialize_message_v2(value)
