"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgcrypto for gen_random_uuid()
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # -------------------------------------------------------------------------
    # strava_apps — shared Strava OAuth app credentials (supports multi-app)
    # -------------------------------------------------------------------------
    op.execute("""
        CREATE TABLE strava_apps (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id   TEXT NOT NULL UNIQUE,
            client_secret_enc BYTEA NOT NULL,
            webhook_verify_token TEXT,
            webhook_subscription_id BIGINT,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # -------------------------------------------------------------------------
    # users
    # -------------------------------------------------------------------------
    op.execute("""
        CREATE TABLE users (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email               TEXT UNIQUE,
            strava_athlete_id   BIGINT UNIQUE,
            komoot_user_id      TEXT,
            komoot_email_enc    BYTEA,
            komoot_password_enc BYTEA,
            is_active           BOOLEAN NOT NULL DEFAULT TRUE,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("CREATE INDEX ix_users_strava_athlete_id ON users (strava_athlete_id)")
    op.execute("CREATE INDEX ix_users_email ON users (email)")

    # -------------------------------------------------------------------------
    # strava_tokens — per-user OAuth tokens for Strava
    # -------------------------------------------------------------------------
    op.execute("""
        CREATE TABLE strava_tokens (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id             UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
            strava_athlete_id   BIGINT NOT NULL UNIQUE,
            strava_app_id       UUID REFERENCES strava_apps (id) ON DELETE SET NULL,
            access_token_enc    BYTEA NOT NULL,
            refresh_token_enc   BYTEA NOT NULL,
            expires_at          TIMESTAMPTZ NOT NULL,
            scope               TEXT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("CREATE INDEX ix_strava_tokens_user_id ON strava_tokens (user_id)")
    op.execute("CREATE INDEX ix_strava_tokens_strava_athlete_id ON strava_tokens (strava_athlete_id)")

    # -------------------------------------------------------------------------
    # subscriptions — billing tier per user
    # -------------------------------------------------------------------------
    op.execute("""
        CREATE TABLE subscriptions (
            id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id                 UUID NOT NULL UNIQUE REFERENCES users (id) ON DELETE CASCADE,
            tier                    TEXT NOT NULL DEFAULT 'free',
            stripe_customer_id      TEXT,
            stripe_subscription_id  TEXT,
            current_period_end      TIMESTAMPTZ,
            cancel_at_period_end    BOOLEAN NOT NULL DEFAULT FALSE,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT subscriptions_tier_check CHECK (tier IN ('free', 'pro', 'business'))
        )
    """)

    op.execute("CREATE INDEX ix_subscriptions_user_id ON subscriptions (user_id)")
    op.execute("CREATE INDEX ix_subscriptions_stripe_customer_id ON subscriptions (stripe_customer_id)")

    # -------------------------------------------------------------------------
    # api_keys — Pro+ programmatic access keys
    # -------------------------------------------------------------------------
    op.execute("""
        CREATE TABLE api_keys (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id     UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
            key_hash    TEXT NOT NULL UNIQUE,
            name        TEXT NOT NULL,
            last_used_at TIMESTAMPTZ,
            expires_at  TIMESTAMPTZ,
            is_active   BOOLEAN NOT NULL DEFAULT TRUE,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("CREATE INDEX ix_api_keys_user_id ON api_keys (user_id)")
    op.execute("CREATE INDEX ix_api_keys_key_hash ON api_keys (key_hash)")

    # -------------------------------------------------------------------------
    # webhook_subscriptions — Strava webhook registrations per app
    # -------------------------------------------------------------------------
    op.execute("""
        CREATE TABLE webhook_subscriptions (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            strava_app_id   UUID NOT NULL REFERENCES strava_apps (id) ON DELETE CASCADE,
            subscription_id BIGINT NOT NULL UNIQUE,
            callback_url    TEXT NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("CREATE INDEX ix_webhook_subscriptions_strava_app_id ON webhook_subscriptions (strava_app_id)")

    # -------------------------------------------------------------------------
    # notification_settings — per-user notification preferences
    # -------------------------------------------------------------------------
    op.execute("""
        CREATE TABLE notification_settings (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id             UUID NOT NULL UNIQUE REFERENCES users (id) ON DELETE CASCADE,
            email_on_sync_error BOOLEAN NOT NULL DEFAULT TRUE,
            email_on_sync_success BOOLEAN NOT NULL DEFAULT FALSE,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # -------------------------------------------------------------------------
    # synced_activities — record of every activity synced between platforms
    # -------------------------------------------------------------------------
    op.execute("""
        CREATE TABLE synced_activities (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id             UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
            komoot_tour_id      TEXT,
            strava_activity_id  BIGINT,
            direction           TEXT NOT NULL,
            status              TEXT NOT NULL DEFAULT 'pending',
            error_message       TEXT,
            synced_at           TIMESTAMPTZ,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT synced_activities_direction_check CHECK (direction IN ('komoot_to_strava', 'strava_to_komoot')),
            CONSTRAINT synced_activities_status_check CHECK (status IN ('pending', 'success', 'failed', 'skipped')),
            CONSTRAINT synced_activities_unique_komoot UNIQUE (user_id, komoot_tour_id),
            CONSTRAINT synced_activities_unique_strava UNIQUE (user_id, strava_activity_id)
        )
    """)

    op.execute("CREATE INDEX ix_synced_activities_user_id ON synced_activities (user_id)")
    op.execute("CREATE INDEX ix_synced_activities_komoot_tour_id ON synced_activities (komoot_tour_id)")
    op.execute("CREATE INDEX ix_synced_activities_strava_activity_id ON synced_activities (strava_activity_id)")
    op.execute("CREATE INDEX ix_synced_activities_status ON synced_activities (status)")

    # -------------------------------------------------------------------------
    # user_sync_state — tracks polling cursors for each user
    # -------------------------------------------------------------------------
    op.execute("""
        CREATE TABLE user_sync_state (
            id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id                 UUID NOT NULL UNIQUE REFERENCES users (id) ON DELETE CASCADE,
            last_komoot_tour_id     TEXT,
            last_komoot_synced_at   TIMESTAMPTZ,
            next_komoot_poll_at     TIMESTAMPTZ,
            last_strava_activity_id BIGINT,
            last_strava_synced_at   TIMESTAMPTZ,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("CREATE INDEX ix_user_sync_state_user_id ON user_sync_state (user_id)")
    op.execute("CREATE INDEX ix_user_sync_state_next_komoot_poll_at ON user_sync_state (next_komoot_poll_at)")

    # -------------------------------------------------------------------------
    # sync_rules — user-defined filters for which activities to sync (Pro+)
    # -------------------------------------------------------------------------
    op.execute("""
        CREATE TABLE sync_rules (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id     UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
            name        TEXT NOT NULL,
            direction   TEXT NOT NULL,
            rule_type   TEXT NOT NULL,
            rule_value  TEXT NOT NULL,
            is_active   BOOLEAN NOT NULL DEFAULT TRUE,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT sync_rules_direction_check CHECK (direction IN ('komoot_to_strava', 'strava_to_komoot', 'both')),
            CONSTRAINT sync_rules_type_check CHECK (rule_type IN ('activity_type', 'min_distance_km', 'max_distance_km', 'sport_type', 'exclude_tag'))
        )
    """)

    op.execute("CREATE INDEX ix_sync_rules_user_id ON sync_rules (user_id)")

    # -------------------------------------------------------------------------
    # job_audit_log — append-only log of background job executions
    # -------------------------------------------------------------------------
    op.execute("""
        CREATE TABLE job_audit_log (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id     UUID REFERENCES users (id) ON DELETE SET NULL,
            job_name    TEXT NOT NULL,
            status      TEXT NOT NULL,
            detail      JSONB,
            duration_ms INTEGER,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT job_audit_log_status_check CHECK (status IN ('started', 'success', 'failed', 'skipped'))
        )
    """)

    op.execute("CREATE INDEX ix_job_audit_log_user_id ON job_audit_log (user_id)")
    op.execute("CREATE INDEX ix_job_audit_log_job_name ON job_audit_log (job_name)")
    op.execute("CREATE INDEX ix_job_audit_log_created_at ON job_audit_log (created_at)")

    # -------------------------------------------------------------------------
    # license_cache — self-hosted license validation cache
    # -------------------------------------------------------------------------
    op.execute("""
        CREATE TABLE license_cache (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            license_key     TEXT NOT NULL UNIQUE,
            tier            TEXT NOT NULL,
            valid_until     TIMESTAMPTZ NOT NULL,
            last_checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            raw_payload     JSONB,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT license_cache_tier_check CHECK (tier IN ('free', 'pro', 'business'))
        )
    """)

    op.execute("CREATE INDEX ix_license_cache_license_key ON license_cache (license_key)")
    op.execute("CREATE INDEX ix_license_cache_valid_until ON license_cache (valid_until)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS license_cache CASCADE")
    op.execute("DROP TABLE IF EXISTS job_audit_log CASCADE")
    op.execute("DROP TABLE IF EXISTS sync_rules CASCADE")
    op.execute("DROP TABLE IF EXISTS user_sync_state CASCADE")
    op.execute("DROP TABLE IF EXISTS synced_activities CASCADE")
    op.execute("DROP TABLE IF EXISTS notification_settings CASCADE")
    op.execute("DROP TABLE IF EXISTS webhook_subscriptions CASCADE")
    op.execute("DROP TABLE IF EXISTS api_keys CASCADE")
    op.execute("DROP TABLE IF EXISTS subscriptions CASCADE")
    op.execute("DROP TABLE IF EXISTS strava_tokens CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
    op.execute("DROP TABLE IF EXISTS strava_apps CASCADE")
    op.execute('DROP EXTENSION IF EXISTS "pgcrypto"')
