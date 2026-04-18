"""Komoot API client — fetches recorded tours and downloads GPX files.

Authentication: HTTP Basic Auth with email + password (confirmed working Dec 2025
via the timschneeb/KomootGPX project).

API base: https://www.komoot.de/api/v007
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import config

logger = logging.getLogger(__name__)

BASE_URL = "https://www.komoot.de/api/v007"

# Maps Komoot sport type strings → Strava sport_type strings.
# Strava's full list: https://developers.strava.com/docs/reference/#api-models-SportType
SPORT_TYPE_MAP: dict[str, str] = {
    # Cycling
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
    # Running
    "jogging": "Run",
    "running": "Run",
    "trail_running": "TrailRun",
    # Hiking / walking
    "hike": "Hike",
    "hiking": "Hike",
    "nordic_walking": "Walk",
    "walking": "Walk",
    # Winter sports
    "skitouring": "BackcountrySki",
    "skitour": "BackcountrySki",
    "snowshoe": "Snowshoe",
    "nordic_ski": "NordicSki",
    "crosscountryskiing": "NordicSki",
    # Water
    "swimming": "Swim",
    "kayaking": "Kayaking",
    "canoeing": "Canoeing",
    "rowing": "Rowing",
    # Other
    "climbing": "RockClimbing",
    "yoga": "Yoga",
    # Fallback
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


def _build_session() -> requests.Session:
    session = requests.Session()
    session.auth = (config.KOMOOT_EMAIL, config.KOMOOT_PASSWORD)
    session.headers.update({"Accept": "application/hal+json, application/json"})
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return session


def _parse_date(raw: str) -> datetime:
    """Parse Komoot date strings — they come in two flavours."""
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
    def __init__(self) -> None:
        self._session = _build_session()

    def _get(self, path: str, **kwargs) -> dict:
        url = f"{BASE_URL}{path}"
        response = self._session.get(url, timeout=30, **kwargs)
        response.raise_for_status()
        return response.json()

    def _iter_tour_pages(self) -> Iterator[dict]:
        """Yield raw tour dicts from all pages."""
        page = 0
        while True:
            data = self._get(
                f"/users/{config.KOMOOT_USER_ID}/tours/",
                params={"type": "tour_recorded", "limit": 50, "page": page},
            )
            tours = data.get("_embedded", {}).get("tours", [])
            if not tours:
                break
            yield from tours
            total_pages = data.get("page", {}).get("totalPages", 1)
            page += 1
            if page >= total_pages:
                break

    def get_tours(self, since: datetime) -> list[Tour]:
        """Return recorded tours newer than *since*, sorted oldest-first."""
        results: list[Tour] = []
        for raw in self._iter_tour_pages():
            try:
                date = _parse_date(raw["date"])
            except (KeyError, ValueError) as exc:
                logger.warning("Skipping tour %s — bad date: %s", raw.get("id"), exc)
                continue

            if date <= since:
                # Tours are returned newest-first; once we drop below *since* we
                # can stop (subsequent pages will only be older).
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

    def download_gpx(self, tour_id: str) -> bytes:
        """Download the GPX file for a tour and return the raw bytes."""
        url = f"{BASE_URL}/tours/{tour_id}.gpx"
        response = self._session.get(url, timeout=60)
        response.raise_for_status()
        logger.debug("Downloaded GPX for tour %s (%d bytes)", tour_id, len(response.content))
        return response.content
