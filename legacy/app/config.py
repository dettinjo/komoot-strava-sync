import os
import sys


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(
            f"[ERROR] Required environment variable '{name}' is not set.\n"
            "Copy .env.template to .env, fill in your credentials, and restart.",
            file=sys.stderr,
        )
        sys.exit(1)
    return value


def _require_int(name: str) -> int:
    return int(_require(name))


class Config:
    # Komoot credentials
    KOMOOT_EMAIL: str = _require("KOMOOT_EMAIL")
    KOMOOT_PASSWORD: str = _require("KOMOOT_PASSWORD")
    KOMOOT_USER_ID: str = _require("KOMOOT_USER_ID")

    # Strava OAuth credentials
    STRAVA_CLIENT_ID: int = _require_int("STRAVA_CLIENT_ID")
    STRAVA_CLIENT_SECRET: str = _require("STRAVA_CLIENT_SECRET")

    # Initial Strava tokens (from scripts/get_token.py, stored in .env)
    STRAVA_ACCESS_TOKEN: str = os.getenv("STRAVA_ACCESS_TOKEN", "")
    STRAVA_REFRESH_TOKEN: str = os.getenv("STRAVA_REFRESH_TOKEN", "")
    STRAVA_TOKEN_EXPIRES_AT: int = int(os.getenv("STRAVA_TOKEN_EXPIRES_AT", "0"))

    # Sync behaviour
    SYNC_INTERVAL_MINUTES: int = int(os.getenv("SYNC_INTERVAL_MINUTES", "30"))
    INITIAL_SYNC_DAYS: int = int(os.getenv("INITIAL_SYNC_DAYS", "30"))

    # Storage
    DATA_DIR: str = os.getenv("DATA_DIR", "/data")

    @property
    def token_file(self) -> str:
        return os.path.join(self.DATA_DIR, "strava_token.json")

    @property
    def db_file(self) -> str:
        return os.path.join(self.DATA_DIR, "sync.db")


config = Config()
