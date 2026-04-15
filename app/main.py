"""Entry point for the Komoot → Strava sync service.

Startup sequence:
  1. Initialise the SQLite database.
  2. Verify Strava tokens are present (fail fast with a clear message if not).
  3. Run an initial sync covering the last INITIAL_SYNC_DAYS days.
  4. Schedule recurring syncs every SYNC_INTERVAL_MINUTES minutes.
  5. Block forever (APScheduler keeps the process alive).

Sync logic per run:
  - Fetch Komoot tours recorded since last_sync_time (or INITIAL_SYNC_DAYS ago).
  - For each tour not yet in the local DB:
      a. Download GPX from Komoot.
      b. Upload GPX to Strava (name, description, sport_type, external_id).
      c. Poll until Strava processes the upload.
      d. Set hide_from_home=True on the created activity.
      e. Record the Komoot tour ID → Strava activity ID mapping in SQLite.
  - Update last_sync_time on success.
"""

import logging
import sys
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app import database as db
from app.config import config
from app.komoot import KomootClient
from app.strava import StravaClient

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core sync function
# ---------------------------------------------------------------------------

def run_sync(komoot: KomootClient, strava: StravaClient) -> None:
    logger.info("=== Starting sync run ===")

    last_sync = db.get_last_sync_time()
    if last_sync is None:
        since = datetime.now(timezone.utc) - timedelta(days=config.INITIAL_SYNC_DAYS)
        logger.info("First run — syncing activities from the last %d days", config.INITIAL_SYNC_DAYS)
    else:
        since = last_sync
        logger.info("Syncing activities since %s", since.isoformat())

    try:
        tours = komoot.get_tours(since=since)
    except Exception as exc:
        logger.error("Failed to fetch Komoot tours: %s", exc)
        return

    if not tours:
        logger.info("No new Komoot tours found — nothing to sync")
        db.set_last_sync_time(datetime.now(timezone.utc))
        return

    synced = 0
    for tour in tours:
        if db.is_synced(tour.id):
            logger.debug("Tour %s already synced — skipping", tour.id)
            continue

        logger.info(
            "Syncing tour %s: %r  [%s  %.1f km]",
            tour.id,
            tour.name,
            tour.strava_sport,
            tour.distance_m / 1000,
        )

        try:
            gpx_bytes = komoot.download_gpx(tour.id)
        except Exception as exc:
            logger.error("Failed to download GPX for tour %s: %s", tour.id, exc)
            continue

        external_id = f"komoot_{tour.id}"
        try:
            upload_id = strava.upload_gpx(
                gpx_bytes=gpx_bytes,
                name=tour.name,
                description=tour.description,
                sport_type=tour.strava_sport,
                external_id=external_id,
            )
        except Exception as exc:
            logger.error("Failed to upload GPX for tour %s: %s", tour.id, exc)
            continue

        try:
            activity_id = strava.poll_upload(upload_id)
        except Exception as exc:
            logger.error("Upload polling failed for tour %s (upload_id=%s): %s", tour.id, upload_id, exc)
            continue

        try:
            strava.update_activity(activity_id, hide_from_home=True)
        except Exception as exc:
            # Non-fatal — the activity was still created successfully
            logger.warning("Could not set hide_from_home on activity %s: %s", activity_id, exc)

        db.mark_synced(tour.id, activity_id)
        synced += 1
        logger.info("  ✓ Tour %s → Strava activity %s", tour.id, activity_id)

    db.set_last_sync_time(datetime.now(timezone.utc))
    logger.info("=== Sync run complete — %d/%d tours synced ===", synced, len(tours))


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("Komoot → Strava sync service starting up")
    logger.info(
        "Config: KOMOOT_USER_ID=%s  SYNC_INTERVAL=%d min  INITIAL_SYNC_DAYS=%d",
        config.KOMOOT_USER_ID,
        config.SYNC_INTERVAL_MINUTES,
        config.INITIAL_SYNC_DAYS,
    )

    db.init_db()

    # Start healthcheck server for Docker / Coolify
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import threading

    class HealthCheckHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
        def log_message(self, format, *args):
            pass

    def start_health_server():
        logger.info("Starting healthcheck server on port 8080")
        try:
            HTTPServer(('0.0.0.0', 8080), HealthCheckHandler).serve_forever()
        except Exception as e:
            logger.error("Healthcheck server failed: %s", e)

    threading.Thread(target=start_health_server, daemon=True).start()

    strava = StravaClient()
    if not strava.is_authorized():
        logger.error(
            "Strava tokens are missing.\n"
            "Run  python scripts/get_token.py  on your local machine to obtain tokens,\n"
            "then add STRAVA_ACCESS_TOKEN, STRAVA_REFRESH_TOKEN, and STRAVA_TOKEN_EXPIRES_AT\n"
            "to your .env file and restart the container."
        )
        sys.exit(1)

    komoot = KomootClient()

    # Run immediately on startup, then on schedule
    run_sync(komoot, strava)

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        run_sync,
        trigger=IntervalTrigger(minutes=config.SYNC_INTERVAL_MINUTES),
        args=[komoot, strava],
        id="sync",
        name="Komoot→Strava sync",
        misfire_grace_time=60,
    )

    logger.info(
        "Scheduler started — next sync in %d minutes",
        config.SYNC_INTERVAL_MINUTES,
    )
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down")


if __name__ == "__main__":
    main()
