from __future__ import annotations
"""API endpoints for managing synchronization."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core import security
from app.db.models.sync import SyncedActivity, UserSyncState
from app.db.models.user import StravaToken, User
from app.services.strava import StravaClient

logger = logging.getLogger(__name__)
router = APIRouter(tags=["sync"])


def _serialize_activity(activity: SyncedActivity | None) -> dict[str, Any] | None:
    if activity is None:
        return None

    return {
        "id": str(activity.id),
        "komoot_tour_id": activity.komoot_tour_id,
        "strava_activity_id": activity.strava_activity_id,
        "sync_direction": activity.sync_direction,
        "sync_status": activity.sync_status,
        "activity_name": activity.activity_name,
        "sport_type": activity.sport_type,
        "distance_m": activity.distance_m,
        "elevation_up_m": activity.elevation_up_m,
        "started_at": activity.started_at.isoformat() if activity.started_at else None,
        "synced_at": activity.synced_at.isoformat(),
    }


@router.get("/status")
async def get_sync_status(
    user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> dict[str, Any]:
    """Return the current sync configuration and recent sync state for the user."""
    state_result = await db.execute(
        select(UserSyncState).where(UserSyncState.user_id == user.id)
    )
    state = state_result.scalar_one_or_none()

    activity_result = await db.execute(
        select(SyncedActivity)
        .where(SyncedActivity.user_id == user.id)
        .order_by(SyncedActivity.synced_at.desc())
        .limit(1)
    )
    latest_activity = activity_result.scalar_one_or_none()

    return {
        "komoot_connected": bool(user.komoot_user_id),
        "strava_connected": bool(user.strava_token),
        "sync_komoot_to_strava": user.sync_komoot_to_strava,
        "sync_strava_to_komoot": user.sync_strava_to_komoot,
        "last_komoot_sync_at": state.last_komoot_sync_at.isoformat() if state and state.last_komoot_sync_at else None,
        "last_strava_sync_at": state.last_strava_sync_at.isoformat() if state and state.last_strava_sync_at else None,
        "last_successful_sync_at": (
            state.last_successful_sync_at.isoformat()
            if state and state.last_successful_sync_at
            else None
        ),
        "total_synced_count": state.total_synced_count if state else 0,
        "last_error": state.last_error if state else None,
        "last_error_at": state.last_error_at.isoformat() if state and state.last_error_at else None,
        "latest_activity": _serialize_activity(latest_activity),
    }


@router.post("/trigger")
async def trigger_sync(
    request: Request,
    user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> dict[str, Any]:
    """Trigger a manual sync of Komoot activities to Strava via background workers."""
    arq_pool = request.app.state.arq_pool
    if not arq_pool:
        return {"status": "error", "message": "Worker pool not available"}
    await arq_pool.enqueue_job("poll_komoot_user", str(user.id))
    return {"status": "queued", "message": "Sync job enqueued successfully"}


@router.post("/rebuild-history")
async def rebuild_history(
    user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
    lookback_days: int = Query(default=180, ge=1, le=730, description="How many days of history to crawl"),
) -> dict[str, Any]:
    """Scan the authenticated user's Strava history for activities originally uploaded
    from Komoot (tagged with external_id=komoot_<tour_id>) and backfill them into the
    local database so the sync engine does not re-upload them on next run.

    This is safe to call multiple times – existing records are skipped (upsert-style).
    """
    # Fetch the user's Strava token
    result = await db.execute(select(StravaToken).where(StravaToken.user_id == user.id))
    token = result.scalar_one_or_none()

    if not token:
        return {"status": "error", "message": "No Strava account linked. Please connect Strava first."}

    access_token = security.decrypt_maybe_plaintext(token.access_token)
    strava = StravaClient(access_token=access_token)

    after_ts = int((datetime.now(timezone.utc) - timedelta(days=lookback_days)).timestamp())

    imported = 0
    skipped = 0
    page = 1

    while True:
        try:
            activities = await strava.get_activities(after=after_ts, page=page, per_page=50)
        except Exception as exc:
            logger.error("rebuild_history: Failed to fetch Strava activities: %s", exc)
            break

        if not activities:
            break

        for activity in activities:
            external_id: Optional[str] = activity.get("external_id") or ""

            # Only consider activities originally uploaded from Komoot
            if not external_id.startswith("komoot_"):
                continue

            komoot_tour_id = external_id.replace("komoot_", "")
            strava_activity_id = str(activity.get("id", ""))

            # Check if already tracked
            check = await db.execute(
                select(SyncedActivity).where(
                    SyncedActivity.user_id == user.id,
                    SyncedActivity.komoot_tour_id == komoot_tour_id,
                )
            )
            if check.scalar_one_or_none():
                skipped += 1
                continue

            # Parse start date safely
            started_at: Optional[datetime] = None
            try:
                started_at = datetime.fromisoformat(activity["start_date"].replace("Z", "+00:00"))
            except Exception:
                pass

            record = SyncedActivity(
                user_id=user.id,
                komoot_tour_id=komoot_tour_id,
                strava_activity_id=strava_activity_id,
                sync_direction="komoot_to_strava",
                sync_status="completed",
                activity_name=activity.get("name"),
                sport_type=activity.get("type"),
                distance_m=activity.get("distance"),
                elevation_up_m=activity.get("total_elevation_gain"),
                started_at=started_at,
                duration_seconds=activity.get("moving_time"),
            )
            db.add(record)
            imported += 1

        await db.commit()
        page += 1

    logger.info(
        "rebuild_history for user %s: imported=%d, skipped=%d (already tracked)",
        user.id, imported, skipped,
    )
    return {
        "status": "success",
        "imported": imported,
        "skipped_already_tracked": skipped,
    }
