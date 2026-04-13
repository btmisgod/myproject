import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class AgentSession(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "agent_sessions"

    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    community_protocol_version: Mapped[str] = mapped_column(String(40), nullable=False)
    runtime_version: Mapped[str] = mapped_column(String(80), nullable=False)
    skill_version: Mapped[str] = mapped_column(String(80), nullable=False)
    onboarding_version: Mapped[str] = mapped_column(String(80), nullable=False)
    last_sync_at: Mapped[datetime] = mapped_column(nullable=False)


class GroupSession(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "group_sessions"
    __table_args__ = (
        UniqueConstraint("agent_session_id", "group_id", name="uq_group_session_agent_session_group"),
    )

    agent_session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_sessions.id", ondelete="CASCADE"), index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    group_session_version: Mapped[str] = mapped_column(String(64), nullable=False)
    declaration_json: Mapped[dict[str, object]] = mapped_column(default=dict)
    last_sync_at: Mapped[datetime] = mapped_column(nullable=False)
