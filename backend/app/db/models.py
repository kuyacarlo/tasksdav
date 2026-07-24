from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    google_sub: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    caldav_username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    caldav_password_hash: Mapped[str] = mapped_column(String(255))
    refresh_token_enc: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lists: Mapped[list["ListMap"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    tasks: Mapped[list["TaskMap"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class ListMap(Base):
    __tablename__ = "list_maps"
    __table_args__ = (UniqueConstraint("user_id", "google_list_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    google_list_id: Mapped[str] = mapped_column(String(128))
    caldav_calendar_id: Mapped[str] = mapped_column(String(128), index=True)
    display_name: Mapped[str] = mapped_column(String(255), default="Tasks")
    ctag: Mapped[str] = mapped_column(String(64), default="1")

    user: Mapped[User] = relationship(back_populates="lists")


class TaskMap(Base):
    __tablename__ = "task_maps"
    __table_args__ = (UniqueConstraint("user_id", "google_task_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    google_task_id: Mapped[str] = mapped_column(String(128))
    google_list_id: Mapped[str] = mapped_column(String(128), index=True)
    ical_uid: Mapped[str] = mapped_column(String(255), index=True)
    etag: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="tasks")
