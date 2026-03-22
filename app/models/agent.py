import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import PresenceState


class Agent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(default=dict)
    is_moderator: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    memberships = relationship("GroupMembership", back_populates="agent", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="agent")
    tasks_claimed = relationship("Task", back_populates="claimed_by_agent")


class GroupMembership(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "group_memberships"
    __table_args__ = (
        UniqueConstraint("group_id", "agent_id", name="uq_group_membership_group_agent"),
    )

    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"))
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"))
    # Community does not assign default identities or permissions at this
    # layer. Keep role as an optional compatibility field for future internal
    # migrations, not as a required membership attribute.
    role: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)

    group = relationship("Group", back_populates="memberships")
    agent = relationship("Agent", back_populates="memberships")


class Presence(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "presence"
    __table_args__ = (
        UniqueConstraint("group_id", "agent_id", name="uq_presence_group_agent"),
    )

    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"))
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"))
    state: Mapped[str] = mapped_column(String(20), default=PresenceState.ONLINE.value)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    group = relationship("Group", back_populates="presence_entries")
    agent = relationship("Agent")

