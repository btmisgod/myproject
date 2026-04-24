import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.common import ORMModel
from app.models.enums import FlowType
from app.services.message_protocol_mapper import normalize_message_to_canonical_v2, serialize_message_v2


class MessageAuthor(BaseModel):
    author_kind: str | None = None
    agent_id: uuid.UUID | None = None


class MessageRelations(BaseModel):
    thread_id: uuid.UUID | None = None
    parent_message_id: uuid.UUID | None = None


class MessageContent(BaseModel):
    text: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    blocks: list[Any] = Field(default_factory=list)
    attachments: list[Any] = Field(default_factory=list)


class StatusBlock(BaseModel):
    workflow_id: str | None = None
    step_id: str | None = None
    lifecycle_phase: str | None = None
    author_agent_id: str | None = None
    author_role: str | None = None
    step_status: str | None = None
    related_message_id: str | None = None


class ContextBlock(BaseModel):
    context_scope: str | None = None
    context_type: str | None = None
    group_context: Any | None = None
    # Deprecated compatibility alias only. New server logic must use
    # group_context as the formal main path.
    channel_context: Any | None = None


class MessageRoutingTarget(BaseModel):
    agent_id: str | None = None


class MessageRouting(BaseModel):
    target: MessageRoutingTarget = Field(default_factory=MessageRoutingTarget)
    mentions: list[Any] = Field(default_factory=list)


class MessageCreate(BaseModel):
    group_id: uuid.UUID
    author_kind: str | None = None
    author: MessageAuthor = Field(default_factory=MessageAuthor)
    flow_type: str
    message_type: str | None = None
    content: MessageContent = Field(default_factory=MessageContent)
    status_block: StatusBlock | dict[str, Any] = Field(default_factory=dict)
    context_block: ContextBlock | dict[str, Any] = Field(default_factory=dict)
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
        if normalized == "status":
            return FlowType.RUN.value
        allowed = {FlowType.START.value, FlowType.RUN.value, FlowType.RESULT.value}
        if normalized not in allowed:
            raise ValueError(f"flow_type must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @model_validator(mode="after")
    def _validate_not_empty_shell(self) -> "MessageCreate":
        def _has_structured_value(value: Any) -> bool:
            if isinstance(value, BaseModel):
                return bool(value.model_dump(exclude_none=True))
            if isinstance(value, dict):
                return bool({k: v for k, v in value.items() if v is not None})
            return bool(value)

        has_text = bool((self.content.text or "").strip())
        has_payload = bool(self.content.payload)
        has_blocks = bool(self.content.blocks)
        has_attachments = bool(self.content.attachments)
        has_status_block = _has_structured_value(self.status_block)
        has_context_block = _has_structured_value(self.context_block)
        if not any((has_text, has_payload, has_blocks, has_attachments, has_status_block, has_context_block)):
            raise ValueError("message must include content, status_block, or context_block")
        return self

    @property
    def agent_id(self) -> uuid.UUID | None:
        return self.author.agent_id

    @property
    def resolved_author_kind(self) -> str | None:
        return self.author.author_kind or self.author_kind

    @property
    def parent_message_id(self) -> uuid.UUID | None:
        return self.relations.parent_message_id

    @property
    def thread_id(self) -> uuid.UUID | None:
        return self.relations.thread_id


class MessageRead(ORMModel):
    id: uuid.UUID
    group_id: uuid.UUID
    author_kind: str | None = None
    author: MessageAuthor
    flow_type: str
    message_type: str | None = None
    content: MessageContent
    status_block: StatusBlock | dict[str, Any] = Field(default_factory=dict)
    context_block: ContextBlock | dict[str, Any] = Field(default_factory=dict)
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
