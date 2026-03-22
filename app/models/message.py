import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Message(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "messages"

    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agents.id"), nullable=True, index=True)
    parent_message_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("messages.id"), nullable=True)
    thread_id: Mapped[uuid.UUID | None] = mapped_column(index=True, nullable=True)
    flow_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    message_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    content: Mapped[dict[str, object]] = mapped_column(default=dict)
    semantics_json: Mapped[dict[str, object]] = mapped_column(default=dict)
    routing_json: Mapped[dict[str, object]] = mapped_column(default=dict)
    extensions_json: Mapped[dict[str, object]] = mapped_column(default=dict)

    group = relationship("Group", back_populates="messages")
    agent = relationship("Agent", back_populates="messages")

