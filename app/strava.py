"""Strava API client — OAuth token management + GPX upload.

Token lifecycle:
  1. Initial tokens are read from environment / .env (populated by scripts/get_token.py).
  2. On startup the client writes them to DATA_DIR/strava_token.json.
  3. Before every API call the token is refreshed if it expires within 5 minutes.
  4. Refreshed tokens are saved back to strava_token.json.

Upload flow (Strava API v3):
  POST /api/v3/uploads          → returns upload_id
  GET  /api/v3/uploads/{id}     → poll until activity_id is available
  PUT  /api/v3/activities/{id}  → set hide_from_home=true
"""

import io
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import config

logger = logging.getLogger(__name__)

STRAVA_BASE = "https://www.strava.com"
TOKEN_URL = f"{STRAVA_BASE}/oauth/token"
UPLOAD_POLL_INTERVAL = 3   # seconds between status polls
UPLOAD_MAX_ATTEMPTS = 30   # max polls before giving up (~90 s)


def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return session


class StravaClient:
    def __init__(self) -> None:
        self._session = _build_session()
        self._token: dict = {}
        self._load_tokens()

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def _token_path(self) -> Path:
        return Path(config.token_file)

    def _load_tokens(self) -> None:
        """Load tokens from file, falling back to env vars if file absent."""
        path = self._token_path()
        if path.exists():
            with path.open() as f:
                self._token = json.load(f)
            logger.debug("Loaded Strava tokens from %s", path)
        else:
            # Bootstrap from environment variables (first run)
            self._token = {
                "access_token": config.STRAVA_ACCESS_TOKEN,
                "refresh_token": config.STRAVA_REFRESH_TOKEN,
                "expires_at": config.STRAVA_TOKEN_EXPIRES_AT,
            }
            if self._token["access_token"]:
                self._save_tokens()
                logger.info("Bootstrapped Strava token from env vars → %s", path)

    def _save_tokens(self) -> None:
        path = self._token_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            json.dump(self._token, f, indent=2)

    def is_authorized(self) -> bool:
        return bool(self._token.get("access_token")) and bool(self._token.get("refresh_token"))

    def _ensure_fresh_token(self) -> None:
        expires_at = int(self._token.get("expires_at", 0))
        now = int(time.time())
        if expires_at - now > 300:
            return  # token still valid for > 5 minutes

        logger.info("Strava access token expired or near expiry — refreshing…")
        resp = requests.post(
            TOKEN_URL,
            data={
                "client_id": config.STRAVA_CLIENT_ID,
                "client_secret": config.STRAVA_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": self._token["refresh_token"],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_at": data["expires_at"],
        }
        self._save_tokens()
        logger.info("Strava token refreshed (expires %s)", datetime.fromtimestamp(data["expires_at"], tz=timezone.utc))

    def _auth_header(self) -> dict[str, str]:
        self._ensure_fresh_token()
        return {"Authorization": f"Bearer {self._token['access_token']}"}

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    def upload_gpx(
        self,
        gpx_bytes: bytes,
        name: str,
        description: str,
        sport_type: str,
        external_id: str,
    ) -> str:
        """Upload a GPX file to Strava and return the upload_id for polling."""
        logger.info("Uploading GPX to Strava: %r (%d bytes)", name, len(gpx_bytes))
        resp = self._session.post(
            f"{STRAVA_BASE}/api/v3/uploads",
            headers=self._auth_header(),
            data={
                "data_type": "gpx",
                "name": name,
                "description": description,
                "sport_type": sport_type,
                "external_id": external_id,
            },
            files={"file": (f"{external_id}.gpx", io.BytesIO(gpx_bytes), "application/gpx+xml")},
            timeout=60,
        )
        resp.raise_for_status()
        upload_id = str(resp.json()["id"])
        logger.debug("Upload accepted — upload_id=%s", upload_id)
        return upload_id

    def poll_upload(self, upload_id: str) -> str:
        """Poll Strava until the upload is processed and return the activity_id."""
        url = f"{STRAVA_BASE}/api/v3/uploads/{upload_id}"
        for attempt in range(1, UPLOAD_MAX_ATTEMPTS + 1):
            resp = self._session.get(url, headers=self._auth_header(), timeout=30)
            resp.raise_for_status()
            data = resp.json()

            error = data.get("error")
            if error:
                raise RuntimeError(f"Strava upload failed: {error}")

            activity_id = data.get("activity_id")
            if activity_id:
                logger.info("Upload processed → activity_id=%s", activity_id)
                return str(activity_id)

            status = data.get("status", "unknown")
            logger.debug("Upload status [%d/%d]: %s", attempt, UPLOAD_MAX_ATTEMPTS, status)
            time.sleep(UPLOAD_POLL_INTERVAL)

        raise TimeoutError(f"Strava upload {upload_id} did not complete after {UPLOAD_MAX_ATTEMPTS} polls")

    def update_activity(self, activity_id: str, hide_from_home: bool = True) -> None:
        """Update activity attributes after upload.

        Note: Strava removed the ability to set visibility='only_me' via API.
        Setting hide_from_home=True mutes the activity from followers' feeds,
        which is the closest available control. Users should set their default
        Strava activity privacy to "Only You" in account settings.
        """
        resp = self._session.put(
            f"{STRAVA_BASE}/api/v3/activities/{activity_id}",
            headers=self._auth_header(),
            json={"hide_from_home": hide_from_home},
            timeout=30,
        )
        resp.raise_for_status()
        logger.debug("Updated activity %s (hide_from_home=%s)", activity_id, hide_from_home)
