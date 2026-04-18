from __future__ import annotations
"""Sync service orchestrating Komoot → Strava synchronization for the SaaS backend."""

import logging
from datetime import timezone, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit_guard
from app.db.models.sync import SyncedActivity, SyncRule, UserSyncState
from app.db.models.user import StravaApp, User
from app.services.komoot import KomootClient
from app.services.strava import StravaClient

logger = logging.getLogger(__name__)


class SyncService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _get_or_create_sync_state(self, user_id: str) -> UserSyncState:
        result = await self.db.execute(
            select(UserSyncState).where(UserSyncState.user_id == user_id)
        )
        state = result.scalar_one_or_none()
        if not state:
            state = UserSyncState(user_id=user_id)
            self.db.add(state)
            await self.db.flush()
        return state

    async def _is_synced(self, user_id: str, tour_id: str) -> bool:
        result = await self.db.execute(
            select(SyncedActivity)
            .where(
                SyncedActivity.user_id == user_id,
                SyncedActivity.komoot_tour_id == tour_id,
                SyncedActivity.sync_status == "completed",
            )
        )
        return result.scalar_one_or_none() is not None

    async def sync_komoot_to_strava(
        self,
        user: User,
        strava_app: StravaApp,
        komoot: KomootClient,
        strava: StravaClient,
    ) -> int:
        """Run the one-way sync from Komoot to Strava for a single user."""
        logger.info("Starting sync for user %s", user.id)

        state = await self._get_or_create_sync_state(str(user.id))

        if state.last_komoot_sync_at is None:
            # First sync: look back 30 days
            since = datetime.now(timezone.utc) - timedelta(days=30)
            logger.info("Initial sync for user %s — looking back to %s", user.id, since)
        else:
            since = state.last_komoot_sync_at
            logger.info("Syncing newer than %s for user %s", since, user.id)

        try:
            tours = await komoot.get_tours(since=since)
        except Exception as exc:
            logger.error("Failed to fetch Komoot tours for user %s: %s", user.id, exc)
            state.last_error = f"Fetch failed: {exc}"
            state.last_error_at = datetime.now(timezone.utc)
            await self.db.commit()
            return 0

        synced_count = 0
        
        # Pull dynamic rules
        rules_stmt = select(SyncRule).where(
            SyncRule.user_id == user.id,
            SyncRule.is_active == True,
            SyncRule.direction.in_(["komoot_to_strava", "both"])
        ).order_by(SyncRule.rule_order.asc())
        rules_res = await self.db.execute(rules_stmt)
        rules = rules_res.scalars().all()

        for tour in tours:
            try:
                # Evaluate filters first
                skip_tour = False
                for rule in rules:
                    # Very simple condition matcher:
                    sport_cond = rule.conditions.get("sport")
                    if sport_cond and sport_cond.lower() == tour.sport.lower():
                        action = rule.actions.get("sync_to")
                        if action == "None":
                            logger.info("Rule '%s' blocked syncing tour %s", rule.name, tour.id)
                            skip_tour = True
                            break
                
                if skip_tour:
                    continue

                # Check DB for duplicate
                if await self._is_synced(str(user.id), tour.id):
                    logger.debug("Tour %s already synced for user %s", tour.id, user.id)
                    continue

                logger.info("Syncing tour %s for %s", tour.id, user.id)

                gpx_bytes = await komoot.download_gpx(tour.id)
                external_id = f"komoot_{tour.id}"

                tier_str = user.subscription.tier if user.subscription else "free"

                # Upload to Strava (guarded by rate limiter)
                upload_id = await rate_limit_guard.call(
                    strava_app.id,
                    tier_str,
                    strava.upload_gpx,
                    gpx_bytes=gpx_bytes,
                    name=tour.name,
                    description=tour.description,
                    sport_type=tour.strava_sport,
                    external_id=external_id,
                )

                # Poll status (guarded)
                activity_id = await rate_limit_guard.call(
                    strava_app.id,
                    tier_str,
                    strava.poll_upload,
                    upload_id=upload_id,
                )

                # Update settings (guarded)
                try:
                    await rate_limit_guard.call(
                        strava_app.id,
                        tier_str,
                        strava.update_activity,
                        activity_id=activity_id,
                        hide_from_home=user.hide_from_home_default,
                    )
                except Exception as e:
                    logger.warning("Could not set hide_from_home on activity %s: %s", activity_id, e)

                # Record in local DB
                activity_record = SyncedActivity(
                    user_id=user.id,
                    komoot_tour_id=tour.id,
                    strava_activity_id=activity_id,
                    sync_direction="komoot_to_strava",
                    sync_status="completed",
                    activity_name=tour.name,
                    sport_type=tour.sport,
                    distance_m=tour.distance_m,
                    elevation_up_m=tour.elevation_up_m,
                    started_at=tour.date,
                )
                self.db.add(activity_record)
                synced_count += 1
                state.total_synced_count += 1
                
                # Commit progressively per successfully uploaded tour
                await self.db.commit()
                
            except Exception as exc:
                logger.error("Failed syncing tour %s for user %s: %s", tour.id, user.id, exc)
                # Keep rolling despite the error
                continue

        # Update last sync marker
        state.last_komoot_sync_at = datetime.now(timezone.utc)
        if synced_count > 0:
            state.last_successful_sync_at = datetime.now(timezone.utc)

        await self.db.commit()
        logger.info("Sync complete for user %s — %d tours synced", user.id, synced_count)
        
        return synced_count
