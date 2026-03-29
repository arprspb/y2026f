from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import UserRole

if TYPE_CHECKING:
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.operator_record)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    voice_commands: Mapped[list["VoiceCommand"]] = relationship(
        back_populates="user",
        foreign_keys="VoiceCommand.user_id",
    )
    confirmations: Mapped[list["VoiceCommand"]] = relationship(
        back_populates="confirmed_by_user",
        foreign_keys="VoiceCommand.confirmed_by_user_id",
    )


class VoiceCommand(Base):
    __tablename__ = "voice_commands"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    audio_filename: Mapped[str] = mapped_column(String(512))
    raw_transcript: Mapped[str] = mapped_column(Text, default="")
    edited_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_command: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parsed_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    user: Mapped["User"] = relationship(
        back_populates="voice_commands",
        foreign_keys=[user_id],
    )
    confirmed_by_user: Mapped["User | None"] = relationship(
        back_populates="confirmations",
        foreign_keys=[confirmed_by_user_id],
    )
