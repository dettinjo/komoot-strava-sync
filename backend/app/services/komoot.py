from __future__ import annotations
"""Asynchronous Komoot API client.

Authentication: HTTP Basic Auth with email + password.
This client is designed for the async SaaS backend.

API base: https://www.komoot.de/api/v007
"""

import logging
from dataclasses import dataclass
from datetime import timezone, datetime
from typing import Any, AsyncGenerator

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://www.komoot.de/api/v007"

# Maps Komoot sport type strings → Strava sport_type strings.
SPORT_TYPE_MAP: dict[str, str] = {
    "touringbicycle": "Ride",
    "road_cycling": "Ride",
    "citybike": "Ride",
    "e_touringbicycle": "EBikeRide",
    "e_road_cycling": "EBikeRide",
    "e_mtb": "EMountainBikeRide",
    "e_mtb_easy": "EMountainBikeRide",
    "mtb": "MountainBikeRide",
    "mtb_easy": "MountainBikeRide",
    "mtb_advanced": "MountainBikeRide",
    "downhillbike": "MountainBikeRide",
    "racebike": "Ride",
    "jogging": "Run",
    "running": "Run",
    "trail_running": "TrailRun",
    "hike": "Hike",
    "hiking": "Hike",
    "nordic_walking": "Walk",
    "walking": "Walk",
    "skitouring": "BackcountrySki",
    "skitour": "BackcountrySki",
    "snowshoe": "Snowshoe",
    "nordic_ski": "NordicSki",
    "crosscountryskiing": "NordicSki",
    "swimming": "Swim",
    "kayaking": "Kayaking",
    "canoeing": "Canoeing",
    "rowing": "Rowing",
    "climbing": "RockClimbing",
    "yoga": "Yoga",
    "_default": "Workout",
}


def _strava_sport(komoot_sport: str) -> str:
    return SPORT_TYPE_MAP.get(komoot_sport, SPORT_TYPE_MAP["_default"])


@dataclass
class Tour:
    id: str
    name: str
    description: str
    sport: str
    strava_sport: str
    date: datetime
    distance_m: float
    elevation_up_m: float


def _parse_date(raw: str) -> datetime:
    """Parse Komoot date strings."""
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    raise ValueError(f"Cannot parse Komoot date: {raw!r}")


class KomootClient:
    def __init__(self, email: str, password: str, user_id: str) -> None:
        self.email = email
        self.password = password
        self.user_id = user_id
        
        # We will reuse this client per instance method call.
        self._client_kwargs: dict[str, Any] = {
            "auth": (email, password),
            "headers": {"Accept": "application/hal+json, application/json"},
            "timeout": httpx.Timeout(30.0),
        }

    async def _get(self, path: str, **kwargs: Any) -> Any:
        url = f"{BASE_URL}{path}"
        async with httpx.AsyncClient(**self._client_kwargs) as client:
            response = await client.get(url, **kwargs)
            response.raise_for_status()
            return response.json()

    async def _iter_tour_pages(self) -> AsyncGenerator[dict[str, Any], None]:
        """Yield raw tour dicts from all pages."""
        page = 0
        while True:
            data = await self._get(
                f"/users/{self.user_id}/tours/",
                params={"type": "tour_recorded", "limit": 50, "page": page},
            )
            tours = data.get("_embedded", {}).get("tours", [])
            if not tours:
                break
            
            for tour in tours:
                yield tour
                
            total_pages = data.get("page", {}).get("totalPages", 1)
            page += 1
            if page >= total_pages:
                break

    async def get_tours(self, since: datetime) -> list[Tour]:
        """Return recorded tours newer than `since`, sorted oldest-first."""
        results: list[Tour] = []
        async for raw in self._iter_tour_pages():
            try:
                date = _parse_date(raw["date"])
            except (KeyError, ValueError) as exc:
                logger.warning("Skipping tour %s — bad date: %s", raw.get("id"), exc)
                continue

            if date <= since:
                break

            description = raw.get("description") or ""
            sport = raw.get("sport", "")

            results.append(
                Tour(
                    id=str(raw["id"]),
                    name=raw.get("name", "Komoot Activity"),
                    description=description,
                    sport=sport,
                    strava_sport=_strava_sport(sport),
                    date=date,
                    distance_m=float(raw.get("distance", 0)),
                    elevation_up_m=float(raw.get("elevation_up", 0)),
                )
            )

        results.sort(key=lambda t: t.date)
        logger.info("Found %d new Komoot tours since %s", len(results), since.isoformat())
        return results

    async def download_gpx(self, tour_id: str) -> bytes:
        """Download the GPX file for a tour and return the raw bytes."""
        url = f"{BASE_URL}/tours/{tour_id}.gpx"
        async with httpx.AsyncClient(**self._client_kwargs) as client:
            response = await client.get(url, timeout=60.0)
            response.raise_for_status()
            logger.debug("Downloaded GPX for tour %s (%d bytes)", tour_id, len(response.content))
            return response.content
