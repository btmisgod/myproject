import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.models.enums import MessageType
from app.schemas.common import ORMModel
from app.services.message_protocol_mapper import normalize_message_to_canonical_v2, serialize_message_v2


class MessageContainer(BaseModel):
    group_id: uuid.UUID


class MessageAuthor(BaseModel):
    agent_id: uuid.UUID | None = None


class MessageRelations(BaseModel):
    thread_id: uuid.UUID | None = None
    parent_message_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None


class MessageBody(BaseModel):
    text: str | None = None
    blocks: list[Any] = Field(default_factory=list)
    attachments: list[Any] = Field(default_factory=list)


class MessageSemantics(BaseModel):
    kind: MessageType
    intent: str | None = None
    topic: str | None = None


class MessageRoutingTarget(BaseModel):
    scope: str | None = None
    agent_id: str | None = None
    agent_label: str | None = None


class MessageRouting(BaseModel):
    target: MessageRoutingTarget = Field(default_factory=MessageRoutingTarget)
    mentions: list[Any] = Field(default_factory=list)
    assignees: list[Any] = Field(default_factory=list)


class MessageExtensions(BaseModel):
    client_request_id: str | None = None
    outbound_correlation_id: str | None = None
    source: str | None = None
    custom: dict[str, Any] = Field(default_factory=dict)


class MessageCreate(BaseModel):
    container: MessageContainer
    author: MessageAuthor = Field(default_factory=MessageAuthor)
    relations: MessageRelations = Field(default_factory=MessageRelations)
    body: MessageBody = Field(default_factory=MessageBody)
    semantics: MessageSemantics
    routing: MessageRouting = Field(default_factory=MessageRouting)
    extensions: MessageExtensions = Field(default_factory=MessageExtensions)

    @model_validator(mode="before")
    @classmethod
    def _normalize_input(cls, value: Any) -> Any:
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return normalize_message_to_canonical_v2(value)
        return value

    @property
    def group_id(self) -> uuid.UUID:
        return self.container.group_id

    @property
    def agent_id(self) -> uuid.UUID | None:
        return self.author.agent_id

    @property
    def task_id(self) -> uuid.UUID | None:
        return self.relations.task_id

    @property
    def parent_message_id(self) -> uuid.UUID | None:
        return self.relations.parent_message_id

    @property
    def thread_id(self) -> uuid.UUID | None:
        return self.relations.thread_id

    @property
    def message_type(self) -> MessageType:
        return self.semantics.kind


class MessageRead(ORMModel):
    id: uuid.UUID
    container: MessageContainer
    author: MessageAuthor
    relations: MessageRelations
    body: MessageBody
    semantics: MessageSemantics
    routing: MessageRouting
    extensions: MessageExtensions
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def _normalize_output(cls, value: Any) -> Any:
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            if "container" in value and "body" in value and "semantics" in value:
                return value
            return normalize_message_to_canonical_v2(value)
        return serialize_message_v2(value)

