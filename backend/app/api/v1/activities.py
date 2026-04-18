from __future__ import annotations
"""API endpoints for managing and viewing synced activities."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core import security
from app.db.models.sync import SyncedActivity
from app.db.models.user import User
from app.services.komoot import KomootClient

router = APIRouter(tags=["activities"])


def _serialize_activity(act: SyncedActivity) -> dict[str, Any]:
    return {
        "id": str(act.id),
        "komoot_tour_id": act.komoot_tour_id,
        "strava_activity_id": act.strava_activity_id,
        "sync_direction": act.sync_direction,
        "sync_status": act.sync_status,
        "activity_name": act.activity_name,
        "sport_type": act.sport_type,
        "distance_m": act.distance_m,
        "elevation_up_m": act.elevation_up_m,
        "started_at": act.started_at.isoformat() if act.started_at else None,
        "synced_at": act.synced_at.isoformat(),
        "duration_seconds": act.duration_seconds,
        "conflict_reason": act.conflict_reason,
        "resolved_at": act.resolved_at.isoformat() if act.resolved_at else None,
    }


@router.get("")
async def get_activities(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> dict[str, Any]:
    """Retrieve the sync history for the current user."""
    stmt = (
        select(SyncedActivity)
        .where(SyncedActivity.user_id == user.id)
        .order_by(SyncedActivity.synced_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    activities = result.scalars().all()

    return {
        "data": [_serialize_activity(act) for act in activities],
        "skip": skip,
        "limit": limit,
        "count": len(activities),
    }


@router.get("/{activity_id}")
async def get_activity_detail(
    activity_id: str,
    user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> dict[str, Any]:
    """Retrieve a single synced activity for the current user."""
    stmt = select(SyncedActivity).where(
        SyncedActivity.id == activity_id,
        SyncedActivity.user_id == user.id,
    )
    result = await db.execute(stmt)
    activity = result.scalar_one_or_none()

    if activity is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Activity not found.")

    return _serialize_activity(activity)


@router.get("/{activity_id}/gpx")
async def download_activity_gpx(
    activity_id: str,
    user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> Response:
    """Download the GPX for a synced Komoot-backed activity."""
    stmt = select(SyncedActivity).where(
        SyncedActivity.id == activity_id,
        SyncedActivity.user_id == user.id,
    )
    result = await db.execute(stmt)
    activity = result.scalar_one_or_none()

    if activity is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Activity not found.")

    if not activity.komoot_tour_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "GPX is only available for activities linked to a Komoot tour.",
        )

    if (
        not user.komoot_email_encrypted
        or not user.komoot_password_encrypted
        or not user.komoot_user_id
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Komoot must be connected before GPX can be downloaded.",
        )

    komoot_email = security.decrypt(user.komoot_email_encrypted)
    komoot_password = security.decrypt(user.komoot_password_encrypted)
    komoot_client = KomootClient(
        email=komoot_email,
        password=komoot_password,
        user_id=user.komoot_user_id,
    )
    gpx_bytes = await komoot_client.download_gpx(activity.komoot_tour_id)

    return Response(
        content=gpx_bytes,
        media_type="application/gpx+xml",
        headers={
            "Content-Disposition": (
                f'attachment; filename="komoot-tour-{activity.komoot_tour_id}.gpx"'
            )
        },
    )
