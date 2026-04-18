from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.user import User


class SyncedActivity(Base):
    __tablename__ = "synced_activities"
    __table_args__ = (
        sa.CheckConstraint(
            "sync_direction IN ('komoot_to_strava', 'strava_to_komoot')",
            name="ck_synced_activities_sync_direction",
        ),
        sa.CheckConstraint(
            "sync_status IN ('pending', 'processing', 'completed', 'failed', 'conflict')",
            name="ck_synced_activities_sync_status",
        ),
        sa.UniqueConstraint("user_id", "komoot_tour_id", name="uq_synced_activities_user_komoot"),
        sa.UniqueConstraint("user_id", "strava_activity_id", name="uq_synced_activities_user_strava"),
        sa.Index("ix_synced_activities_user_synced_at", "user_id", "synced_at"),
    )

    id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    komoot_tour_id: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    strava_activity_id: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    sync_direction: Mapped[str] = mapped_column(sa.String, nullable=False)
    synced_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    sync_status: Mapped[str] = mapped_column(
        sa.String, nullable=False, default="completed"
    )
    activity_name: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    sport_type: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    distance_m: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    elevation_up_m: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    conflict_reason: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="synced_activities")


class UserSyncState(Base):
    __tablename__ = "user_sync_state"

    user_id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    last_komoot_sync_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    last_strava_sync_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    last_successful_sync_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    total_synced_count: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0
    )
    last_error: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    last_error_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )


class SyncRule(Base):
    __tablename__ = "sync_rules"
    __table_args__ = (
        sa.CheckConstraint(
            "direction IN ('komoot_to_strava', 'strava_to_komoot', 'both')",
            name="ck_sync_rules_direction",
        ),
        sa.Index("ix_sync_rules_user_order", "user_id", "rule_order"),
    )

    id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    direction: Mapped[str] = mapped_column(sa.String, nullable=False)
    rule_order: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    conditions: Mapped[dict] = mapped_column(sa.JSON, nullable=False)
    actions: Mapped[dict] = mapped_column(sa.JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="sync_rules")


class JobAuditLog(Base):
    __tablename__ = "job_audit_log"

    id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    job_id: Mapped[str] = mapped_column(sa.String, nullable=False)
    job_type: Mapped[str] = mapped_column(sa.String, nullable=False)
    user_id: Mapped[Optional[UUID]] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(sa.String, nullable=False, default="queued")
    priority: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=5)
    enqueued_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    retry_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    payload: Mapped[Optional[dict]] = mapped_column(sa.JSON, nullable=True)
