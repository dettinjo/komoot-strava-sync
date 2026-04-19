from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit_guard
from app.db.models.sync import SyncedActivity, SyncRule, UserSyncState
from app.db.models.user import StravaApp, User
from app.services.komoot import KomootClient, Tour
from app.services.strava import StravaClient

logger = logging.getLogger(__name__)


def _match_condition(tour: Tour, conditions: dict[str, Any]) -> bool:
    """Return True if all conditions match the tour. All conditions must pass (AND logic)."""
    distance_km = (tour.distance_m or 0) / 1000.0
    elevation_m = tour.elevation_up_m or 0

    for key, value in conditions.items():
        if key == "sport_type":
            # {"sport_type": {"is": ["e_road_cycling", "e_touringbicycle"]}}
            # {"sport_type": {"is_not": ["hike"]}}
            if isinstance(value, dict):
                if "is" in value:
                    allowed = [s.lower() for s in value["is"]]
                    if tour.sport.lower() not in allowed:
                        return False
                if "is_not" in value:
                    blocked = [s.lower() for s in value["is_not"]]
                    if tour.sport.lower() in blocked:
                        return False
            else:
                # Legacy: {"sport_type": "E-Bike"} — plain equality
                if tour.sport.lower() != str(value).lower():
                    return False

        elif key == "sport":
            # Legacy alias kept for backwards compatibility
            if tour.sport.lower() != str(value).lower():
                return False

        elif key == "distance_km":
            if isinstance(value, dict):
                if "gt" in value and not (distance_km > value["gt"]):
                    return False
                if "lt" in value and not (distance_km < value["lt"]):
                    return False
                if "between" in value:
                    lo, hi = value["between"]
                    if not (lo <= distance_km <= hi):
                        return False
            else:
                return False

        elif key == "elevation_m":
            if isinstance(value, dict):
                if "gt" in value and not (elevation_m > value["gt"]):
                    return False
                if "lt" in value and not (elevation_m < value["lt"]):
                    return False
            else:
                return False

        elif key == "name_contains":
            if str(value).lower() not in tour.name.lower():
                return False

    return True


def _apply_action(
    tour: Tour, actions: dict[str, Any], user: User
) -> tuple[bool, Tour, dict[str, Any]]:
    """Apply rule actions to a tour.

    Returns (skip, modified_tour, extra_kwargs) where extra_kwargs are passed to
    the Strava update call (e.g. hide_from_home override, description suffix).
    """
    extras: dict[str, Any] = {}

    if actions.get("skip") or actions.get("sync_to") == "None":
        return True, tour, extras

    if "set_sport_type" in actions:
        tour = Tour(
            id=tour.id,
            name=tour.name,
            description=tour.description,
            sport=tour.sport,
            strava_sport=actions["set_sport_type"],
            date=tour.date,
            distance_m=tour.distance_m,
            elevation_up_m=tour.elevation_up_m,
        )

    if "name_template" in actions:
        tmpl = actions["name_template"]
        try:
            new_name = tmpl.format(
                name=tour.name,
                distance=(tour.distance_m or 0) / 1000,
                elevation=int(tour.elevation_up_m or 0),
            )
            tour = Tour(
                id=tour.id,
                name=new_name,
                description=tour.description,
                sport=tour.sport,
                strava_sport=tour.strava_sport,
                date=tour.date,
                distance_m=tour.distance_m,
                elevation_up_m=tour.elevation_up_m,
            )
        except Exception:
            pass

    if "append_description" in actions:
        suffix = actions["append_description"]
        extras["description_suffix"] = suffix

    if "set_hide_from_home" in actions:
        extras["hide_from_home"] = bool(actions["set_hide_from_home"])

    return False, tour, extras


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
            select(SyncedActivity).where(
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
            since = datetime.now(UTC) - timedelta(days=30)
            logger.info("Initial sync for user %s — looking back to %s", user.id, since)
        else:
            since = state.last_komoot_sync_at
            logger.info("Syncing newer than %s for user %s", since, user.id)

        try:
            tours = await komoot.get_tours(since=since)
        except Exception as exc:
            logger.error("Failed to fetch Komoot tours for user %s: %s", user.id, exc)
            state.last_error = f"Fetch failed: {exc}"
            state.last_error_at = datetime.now(UTC)
            await self.db.commit()
            return 0

        synced_count = 0

        # Pull dynamic rules
        rules_stmt = (
            select(SyncRule)
            .where(
                SyncRule.user_id == user.id,
                SyncRule.is_active == True,
                SyncRule.direction.in_(["komoot_to_strava", "both"]),
            )
            .order_by(SyncRule.rule_order.asc())
        )
        rules_res = await self.db.execute(rules_stmt)
        rules = rules_res.scalars().all()

        for tour in tours:
            try:
                # Evaluate rules (first match wins)
                skip_tour = False
                rule_extras: dict[str, Any] = {}
                for rule in rules:
                    if _match_condition(tour, rule.conditions):
                        skip_tour, tour, rule_extras = _apply_action(tour, rule.actions, user)
                        if skip_tour:
                            logger.info("Rule '%s' skipped tour %s", rule.name, tour.id)
                        else:
                            logger.debug("Rule '%s' modified tour %s", rule.name, tour.id)
                        break  # first matching rule wins

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

                # Update settings (guarded) — rule may override hide_from_home
                hide = rule_extras.get("hide_from_home", user.hide_from_home_default)
                try:
                    await rate_limit_guard.call(
                        strava_app.id,
                        tier_str,
                        strava.update_activity,
                        activity_id=activity_id,
                        hide_from_home=hide,
                    )
                except Exception as e:
                    logger.warning(
                        "Could not set hide_from_home on activity %s: %s", activity_id, e
                    )

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
        state.last_komoot_sync_at = datetime.now(UTC)
        if synced_count > 0:
            state.last_successful_sync_at = datetime.now(UTC)

        await self.db.commit()
        logger.info("Sync complete for user %s — %d tours synced", user.id, synced_count)

        return synced_count
