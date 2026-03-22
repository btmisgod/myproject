from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Group(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "groups"

    name: Mapped[str] = mapped_column(String(120), index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    group_type: Mapped[str] = mapped_column(String(40), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(default=dict)

    memberships = relationship("GroupMembership", back_populates="group", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="group")
    presence_entries = relationship("Presence", back_populates="group", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="group")

