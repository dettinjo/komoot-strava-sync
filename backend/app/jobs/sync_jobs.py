from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core import security
from app.core.rate_limit import rate_limit_guard
from app.db.models.subscription import Subscription
from app.db.models.sync import JobAuditLog, SyncedActivity
from app.db.models.user import StravaApp, StravaToken, User
from app.db.session import AsyncSessionLocal
from app.services.komoot import KomootClient
from app.services.strava import StravaClient
from app.services.sync import SyncService

logger = logging.getLogger(__name__)

_MIN_POLL_INTERVAL: dict[str, int] = {"free": 120, "pro": 10, "lifetime": 10, "business": 10}


async def _get_valid_strava_access_token(user: User) -> str:
    """Return a usable Strava access token, refreshing it when near expiry."""
    if not user.strava_token:
        raise ValueError("User has no Strava token")

    access_token = security.decrypt_maybe_plaintext(user.strava_token.access_token)
    refresh_due_at = user.strava_token.expires_at - timedelta(minutes=5)
    if refresh_due_at > datetime.now(UTC):
        return access_token

    refresh_token = security.decrypt_maybe_plaintext(user.strava_token.refresh_token)
    refreshed = await StravaClient.refresh_access_token(refresh_token)

    user.strava_token.access_token = security.encrypt(refreshed["access_token"])
    user.strava_token.refresh_token = security.encrypt(refreshed["refresh_token"])
    user.strava_token.expires_at = datetime.fromtimestamp(refreshed["expires_at"], tz=UTC)
    user.strava_token.last_refreshed_at = datetime.now(UTC)

    logger.info("Refreshed Strava access token for user %s", user.id)
    return refreshed["access_token"]


async def poll_komoot_user(ctx: dict, user_id: str) -> None:
    """Fetches new Komoot tours and uploads them to Strava for one user."""
    job_id = ctx.get("job_id", "unknown")
    logger.info("Executing poll_komoot_user job %s for user %s", job_id, user_id)

    async with AsyncSessionLocal() as db:
        audit = JobAuditLog(
            job_id=job_id,
            job_type="poll_komoot_user",
            user_id=user_id,
            status="running",
            priority=5,
            enqueued_at=datetime.now(UTC),
            started_at=datetime.now(UTC),
        )
        db.add(audit)
        await db.commit()

        error_message: str | None = None
        try:
            stmt = (
                select(User)
                .where(User.id == user_id)
                .options(selectinload(User.strava_token), selectinload(User.subscription))
            )
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.warning("poll_komoot_user: User %s not found.", user_id)
                return

            if not user.sync_komoot_to_strava:
                logger.debug(
                    "poll_komoot_user: User %s has komoot_to_strava sync disabled.", user_id
                )
                return

            if (
                not user.komoot_email_encrypted
                or not user.komoot_password_encrypted
                or not user.komoot_user_id
            ):
                logger.warning("poll_komoot_user: User %s missing Komoot credentials.", user_id)
                return

            if not user.strava_token:
                logger.warning("poll_komoot_user: User %s missing Strava token.", user_id)
                return

            stmt_app = select(StravaApp).where(StravaApp.id == user.strava_token.strava_app_id)
            result_app = await db.execute(stmt_app)
            strava_app = result_app.scalar_one_or_none()

            if not strava_app:
                logger.error("poll_komoot_user: StravaApp not found for User %s", user_id)
                return

            komoot_email = security.decrypt(user.komoot_email_encrypted)
            komoot_password = security.decrypt(user.komoot_password_encrypted)

            komoot_client = KomootClient(
                email=komoot_email,
                password=komoot_password,
                user_id=user.komoot_user_id,
            )

            access_token = await _get_valid_strava_access_token(user)
            strava_client = StravaClient(access_token=access_token)

            sync_service = SyncService(db)
            await sync_service.sync_komoot_to_strava(
                user=user,
                strava_app=strava_app,
                komoot=komoot_client,
                strava=strava_client,
            )

            tier = user.subscription.tier if user.subscription else "free"
            min_interval = _MIN_POLL_INTERVAL.get(tier, 120)
            interval = max(user.komoot_poll_interval_min, min_interval)

            user.last_komoot_poll_at = datetime.now(UTC)
            user.next_komoot_poll_at = datetime.now(UTC) + timedelta(minutes=interval)
            await db.commit()

        except Exception as exc:
            error_message = str(exc)
            logger.error("poll_komoot_user failed for user %s: %s", user_id, exc)
        finally:
            audit.status = "failed" if error_message else "completed"
            audit.completed_at = datetime.now(UTC)
            audit.error_message = error_message
            await db.commit()


async def process_strava_activity(ctx: dict, athlete_id: str, activity_id: str) -> None:
    """Handles a Strava webhook event by recording the inbound activity.

    Full Strava → Komoot reverse sync is architecturally blocked because Komoot
    does not expose a public GPX-upload API endpoint. The groundwork below is
    complete and ready: it fetches the Strava activity metadata, records it in
    the database as a 'strava_to_komoot' entry, and logs the limitation.

    When a Komoot upload endpoint becomes available (via reverse-engineered mobile
    API or official partner access), replace the TODO block with the Komoot upload call.
    """
    logger.info("process_strava_activity: athlete=%s activity=%s", athlete_id, activity_id)

    async with AsyncSessionLocal() as db:
        # Resolve the local user from Strava's athlete id.
        stmt = (
            select(User)
            .join(StravaToken, StravaToken.user_id == User.id)
            .where(StravaToken.strava_athlete_id == int(athlete_id))
            .options(
                selectinload(User.strava_token),
                selectinload(User.subscription),
            )
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(
                "process_strava_activity: No user found for Strava athlete %s.",
                athlete_id,
            )
            return

        if not user.strava_token:
            logger.warning("process_strava_activity: User %s has no Strava token.", user.id)
            return

        # Avoid duplicate processing
        existing = await db.execute(
            select(SyncedActivity).where(
                SyncedActivity.user_id == user.id,
                SyncedActivity.strava_activity_id == activity_id,
                SyncedActivity.sync_direction == "strava_to_komoot",
            )
        )
        if existing.scalar_one_or_none():
            logger.info(
                "process_strava_activity: activity %s already recorded for user %s — skipping.",
                activity_id,
                user.id,
            )
            return

        # Fetch activity metadata from Strava
        access_token = await _get_valid_strava_access_token(user)
        strava_client = StravaClient(access_token=access_token)
        stmt_app = select(StravaApp).where(StravaApp.id == user.strava_token.strava_app_id)
        result_app = await db.execute(stmt_app)
        strava_app = result_app.scalar_one_or_none()

        if not strava_app:
            logger.error("process_strava_activity: StravaApp not found for user %s", user.id)
            return

        tier_str = user.subscription.tier if user.subscription else "free"
        try:
            activity_data = await rate_limit_guard.call(
                strava_app.id,
                tier_str,
                strava_client.get_activity,
                activity_id=activity_id,
            )
        except Exception as exc:
            logger.error(
                "process_strava_activity: Failed to fetch Strava activity %s: %s",
                activity_id,
                exc,
            )
            return

        # Record in DB as pending reverse sync
        started_at = None
        try:
            started_at = datetime.fromisoformat(
                activity_data.get("start_date", "").replace("Z", "+00:00")
            )
        except Exception:
            pass

        record = SyncedActivity(
            user_id=user.id,
            strava_activity_id=activity_id,
            sync_direction="strava_to_komoot",
            sync_status="pending",  # Komoot upload not possible yet
            activity_name=activity_data.get("name"),
            sport_type=activity_data.get("type"),
            distance_m=activity_data.get("distance"),
            elevation_up_m=activity_data.get("total_elevation_gain"),
            started_at=started_at,
            duration_seconds=activity_data.get("moving_time"),
            conflict_reason=(
                "Komoot upload API not publicly available. "
                "Record saved — will be retried when endpoint is known."
            ),
        )
        db.add(record)
        await db.commit()

        logger.info(
            "process_strava_activity: Recorded activity %s for user %s as pending reverse sync.",
            activity_id,
            user.id,
        )


async def komoot_poll_scheduler(ctx: dict) -> None:
    """Cron: queries users with next_komoot_poll_at <= now, enqueues poll jobs."""
    logger.info("Running komoot_poll_scheduler cron job")

    redis = ctx.get("redis")
    if not redis:
        logger.error("Redis not available in Worker ctx.")
        return

    now = datetime.now(UTC)

    async with AsyncSessionLocal() as db:
        # Fetch active StravaApp id for budget check (use the first active app)
        from app.db.models.user import StravaApp as _StravaApp

        app_result = await db.execute(
            select(_StravaApp.id).where(_StravaApp.is_active == True).limit(1)  # noqa: E712
        )
        strava_app_id = app_result.scalar_one_or_none()

        # Check daily Strava budget — skip free-tier users when > 800
        daily_count = await rate_limit_guard.daily_count(strava_app_id) if strava_app_id else 0
        budget_exhausted_for_free = daily_count > 800
        if budget_exhausted_for_free:
            logger.warning(
                "Daily Strava budget at %d — free-tier polling suspended this cycle.", daily_count
            )

        stmt = (
            select(User.id, Subscription.tier)
            .outerjoin(Subscription, Subscription.user_id == User.id)
            .where(
                User.is_active == True,  # noqa: E712
                User.sync_komoot_to_strava == True,  # noqa: E712
                (User.next_komoot_poll_at <= now) | (User.next_komoot_poll_at == None),  # noqa: E711
            )
        )
        result = await db.execute(stmt)
        rows = result.all()

        enqueued = 0
        skipped_budget = 0
        for uid, tier in rows:
            tier = tier or "free"
            if budget_exhausted_for_free and tier == "free":
                skipped_budget += 1
                continue
            await redis.enqueue_job("poll_komoot_user", str(uid))
            enqueued += 1

        logger.info(
            "Scheduler: enqueued=%d, skipped_free_budget=%d (daily=%d)",
            enqueued,
            skipped_budget,
            daily_count,
        )
