from __future__ import annotations

from datetime import datetime, UTC
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.subscription import Subscription
    from app.db.models.sync import SyncRule, SyncedActivity


class StravaApp(Base):
    __tablename__ = "strava_apps"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[str] = mapped_column(sa.String, unique=True, nullable=False)
    client_secret: Mapped[bytes] = mapped_column(sa.LargeBinary, nullable=False)
    display_name: Mapped[str] = mapped_column(sa.String, nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    daily_requests: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    daily_reset_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    email: Mapped[str] = mapped_column(
        sa.String,
        unique=True,
        nullable=False,
        index=True,
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    password_hash: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    is_admin: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)

    # Komoot credentials (encrypted)
    komoot_email_encrypted: Mapped[bytes | None] = mapped_column(
        sa.LargeBinary, nullable=True
    )
    komoot_password_encrypted: Mapped[bytes | None] = mapped_column(
        sa.LargeBinary, nullable=True
    )
    komoot_key_version: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=1
    )
    komoot_user_id: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    komoot_connected_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    komoot_poll_interval_min: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=60
    )
    next_komoot_poll_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    last_komoot_poll_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    # Sync preferences
    sync_komoot_to_strava: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=True
    )
    sync_strava_to_komoot: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False
    )
    hide_from_home_default: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=True
    )
    timezone: Mapped[str] = mapped_column(sa.String, nullable=False, default="UTC")

    # Relationships
    subscription: Mapped[Subscription] = relationship(
        "Subscription", back_populates="user", uselist=False
    )
    strava_token: Mapped[StravaToken] = relationship(
        "StravaToken", back_populates="user", uselist=False
    )
    sync_rules: Mapped[list[SyncRule]] = relationship(
        "SyncRule", back_populates="user"
    )
    synced_activities: Mapped[list[SyncedActivity]] = relationship(
        "SyncedActivity", back_populates="user"
    )


class StravaToken(Base):
    __tablename__ = "strava_tokens"

    user_id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    strava_app_id: Mapped[int | None] = mapped_column(
        sa.Integer,
        sa.ForeignKey("strava_apps.id"),
        nullable=True,
    )
    strava_athlete_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        unique=True,
        nullable=False,
        index=True,
    )
    access_token: Mapped[bytes] = mapped_column(sa.LargeBinary, nullable=False)
    refresh_token: Mapped[bytes] = mapped_column(sa.LargeBinary, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    scope: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
        default="activity:write,activity:read_all",
    )
    connected_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    last_refreshed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="strava_token")
