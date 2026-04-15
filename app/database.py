import sqlite3
import logging
from datetime import datetime, timezone
from app.config import config

logger = logging.getLogger(__name__)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.db_file)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS synced_activities (
                komoot_tour_id   TEXT PRIMARY KEY,
                strava_activity_id TEXT NOT NULL,
                synced_at        TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_state (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.commit()
    logger.info("Database initialised at %s", config.db_file)


def is_synced(komoot_tour_id: str) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM synced_activities WHERE komoot_tour_id = ?",
            (str(komoot_tour_id),),
        ).fetchone()
    return row is not None


def mark_synced(komoot_tour_id: str, strava_activity_id: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO synced_activities
                (komoot_tour_id, strava_activity_id, synced_at)
            VALUES (?, ?, ?)
            """,
            (str(komoot_tour_id), str(strava_activity_id), now),
        )
        conn.commit()
    logger.debug("Marked komoot tour %s → strava activity %s", komoot_tour_id, strava_activity_id)


def get_last_sync_time() -> datetime | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT value FROM sync_state WHERE key = 'last_sync_time'"
        ).fetchone()
    if row:
        return datetime.fromisoformat(row["value"])
    return None


def set_last_sync_time(dt: datetime) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO sync_state (key, value) VALUES ('last_sync_time', ?)",
            (dt.isoformat(),),
        )
        conn.commit()
