from __future__ import annotations

"""Initial schema aligned with the current SQLAlchemy models.

Revision ID: 001
Revises:
Create Date: 2026-04-17 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "strava_apps",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.String(), nullable=False, unique=True),
        sa.Column("client_secret", sa.LargeBinary(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("daily_requests", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "daily_reset_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_hash", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("komoot_email_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("komoot_password_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("komoot_key_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("komoot_user_id", sa.String(), nullable=True),
        sa.Column("komoot_connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "komoot_poll_interval_min", sa.Integer(), nullable=False, server_default=sa.text("60")
        ),
        sa.Column("next_komoot_poll_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_komoot_poll_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "sync_komoot_to_strava", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "sync_strava_to_komoot", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "hide_from_home_default", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "timezone", sa.String(), nullable=False, server_default=sa.text("'timezone.utc'")
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "strava_tokens",
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "strava_app_id",
            sa.Integer(),
            sa.ForeignKey("strava_apps.id"),
            nullable=True,
        ),
        sa.Column("strava_athlete_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("access_token", sa.LargeBinary(), nullable=False),
        sa.Column("refresh_token", sa.LargeBinary(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "scope",
            sa.String(),
            nullable=False,
            server_default=sa.text("'activity:write,activity:read_all'"),
        ),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_refreshed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_strava_tokens_strava_athlete_id",
        "strava_tokens",
        ["strava_athlete_id"],
        unique=True,
    )

    op.create_table(
        "subscriptions",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("stripe_customer_id", sa.String(), nullable=True, unique=True),
        sa.Column("stripe_subscription_id", sa.String(), nullable=True, unique=True),
        sa.Column("stripe_price_id", sa.String(), nullable=True),
        sa.Column("tier", sa.String(), nullable=False, server_default=sa.text("'free'")),
        sa.Column("status", sa.String(), nullable=False, server_default=sa.text("'active'")),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "activities_synced_this_period",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("period_reset_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("tier IN ('free', 'pro', 'business')", name="ck_subscriptions_tier"),
        sa.CheckConstraint(
            "status IN ('active', 'past_due', 'canceled', 'trialing')",
            name="ck_subscriptions_status",
        ),
    )

    op.create_table(
        "api_keys",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key_hash", sa.String(), nullable=False, unique=True),
        sa.Column("key_prefix", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"], unique=False)

    op.create_table(
        "webhook_subscriptions",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("secret", sa.String(), nullable=False),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("last_delivery_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.create_index(
        "ix_webhook_subscriptions_user_id",
        "webhook_subscriptions",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "notification_settings",
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "email_on_sync_error", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "email_on_daily_summary", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "email_on_conflict", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("webhook_on_sync", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "license_cache",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("license_key", sa.String(), nullable=False, unique=True),
        sa.Column("tier", sa.String(), nullable=False),
        sa.Column("max_users", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.Column("issued_to_hash", sa.String(), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("grace_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "synced_activities",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("komoot_tour_id", sa.String(), nullable=True),
        sa.Column("strava_activity_id", sa.String(), nullable=True),
        sa.Column("sync_direction", sa.String(), nullable=False),
        sa.Column(
            "synced_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "sync_status", sa.String(), nullable=False, server_default=sa.text("'completed'")
        ),
        sa.Column("activity_name", sa.String(), nullable=True),
        sa.Column("sport_type", sa.String(), nullable=True),
        sa.Column("distance_m", sa.Float(), nullable=True),
        sa.Column("elevation_up_m", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("conflict_reason", sa.String(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "sync_direction IN ('komoot_to_strava', 'strava_to_komoot')",
            name="ck_synced_activities_sync_direction",
        ),
        sa.CheckConstraint(
            "sync_status IN ('pending', 'processing', 'completed', 'failed', 'conflict')",
            name="ck_synced_activities_sync_status",
        ),
        sa.UniqueConstraint("user_id", "komoot_tour_id", name="uq_synced_activities_user_komoot"),
        sa.UniqueConstraint(
            "user_id", "strava_activity_id", name="uq_synced_activities_user_strava"
        ),
    )
    op.create_index("ix_synced_activities_user_id", "synced_activities", ["user_id"], unique=False)
    op.create_index(
        "ix_synced_activities_synced_at", "synced_activities", ["synced_at"], unique=False
    )
    op.create_index(
        "ix_synced_activities_user_synced_at",
        "synced_activities",
        ["user_id", "synced_at"],
        unique=False,
    )

    op.create_table(
        "user_sync_state",
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("last_komoot_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_strava_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_successful_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_synced_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "sync_rules",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("direction", sa.String(), nullable=False),
        sa.Column("rule_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("conditions", sa.JSON(), nullable=False),
        sa.Column("actions", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "direction IN ('komoot_to_strava', 'strava_to_komoot', 'both')",
            name="ck_sync_rules_direction",
        ),
    )
    op.create_index("ix_sync_rules_user_id", "sync_rules", ["user_id"], unique=False)
    op.create_index(
        "ix_sync_rules_user_order", "sync_rules", ["user_id", "rule_order"], unique=False
    )

    op.create_table(
        "job_audit_log",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("job_type", sa.String(), nullable=False),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(), nullable=False, server_default=sa.text("'queued'")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("5")),
        sa.Column("enqueued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("payload", sa.JSON(), nullable=True),
    )
    op.create_index("ix_job_audit_log_user_id", "job_audit_log", ["user_id"], unique=False)
    op.create_index("ix_job_audit_log_enqueued_at", "job_audit_log", ["enqueued_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_job_audit_log_enqueued_at", table_name="job_audit_log")
    op.drop_index("ix_job_audit_log_user_id", table_name="job_audit_log")
    op.drop_table("job_audit_log")

    op.drop_index("ix_sync_rules_user_order", table_name="sync_rules")
    op.drop_index("ix_sync_rules_user_id", table_name="sync_rules")
    op.drop_table("sync_rules")

    op.drop_table("user_sync_state")

    op.drop_index("ix_synced_activities_user_synced_at", table_name="synced_activities")
    op.drop_index("ix_synced_activities_synced_at", table_name="synced_activities")
    op.drop_index("ix_synced_activities_user_id", table_name="synced_activities")
    op.drop_table("synced_activities")

    op.drop_table("license_cache")
    op.drop_table("notification_settings")

    op.drop_index("ix_webhook_subscriptions_user_id", table_name="webhook_subscriptions")
    op.drop_table("webhook_subscriptions")

    op.drop_index("ix_api_keys_user_id", table_name="api_keys")
    op.drop_table("api_keys")

    op.drop_table("subscriptions")

    op.drop_index("ix_strava_tokens_strava_athlete_id", table_name="strava_tokens")
    op.drop_table("strava_tokens")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    op.drop_table("strava_apps")
