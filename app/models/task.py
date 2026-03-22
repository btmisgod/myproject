import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import TaskStatus


class Task(UUIDMixin, TimestampMixin, Base):
    # Historical persistence model retained as a group-scoped collaboration
    # object helper. Community semantics should continue to be derived from
    # groups, messages, protocols, and contracts rather than from a public
    # community-level task model.
    __tablename__ = "tasks"

    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=TaskStatus.PENDING.value, nullable=False)
    claimed_by_agent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(default=dict)
    result_summary: Mapped[dict[str, object]] = mapped_column(default=dict)

    group = relationship("Group", back_populates="tasks")
    claimed_by_agent = relationship("Agent", back_populates="tasks_claimed")

