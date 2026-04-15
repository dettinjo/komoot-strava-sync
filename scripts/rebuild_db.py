import logging
import sys
from datetime import datetime, timezone
import os

# Ensure the app module is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import database as db
from app.strava import StravaClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
logger = logging.getLogger(__name__)

STRAVA_BASE = "https://www.strava.com"

def main():
    logger.info("Connecting to database...")
    db.init_db()

    logger.info("Authenticating with Strava...")
    strava = StravaClient()
    
    if not strava.is_authorized():
        logger.error("Strava is not authorized. Please ensure you have a valid token.")
        sys.exit(1)

    logger.info("Fetching activities from Strava...")
    
    page = 1
    per_page = 200
    synced_count = 0
    latest_date = None

    while True:
        logger.info(f"Fetching page {page}...")
        resp = strava._session.get(
            f"{STRAVA_BASE}/api/v3/athlete/activities",
            headers=strava._auth_header(),
            params={"page": page, "per_page": per_page},
            timeout=30,
        )
        resp.raise_for_status()
        activities = resp.json()
        
        if not activities:
            break

        for activity in activities:
            external_id = activity.get("external_id")
            
            # Record the latest date from all activities to potentially update last_sync_time
            start_date_str = activity.get("start_date")
            if start_date_str:
                activity_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
                if latest_date is None or activity_date > latest_date:
                    latest_date = activity_date

            if external_id and external_id.startswith("komoot_"):
                tour_id = external_id.replace("komoot_", "")
                
                # Check if it has a trailing .gpx (Strava sometimes appends .gpx depending on how it was uploaded)
                if tour_id.endswith(".gpx"):
                    tour_id = tour_id[:-4]

                activity_id = str(activity["id"])
                
                if not db.is_synced(tour_id):
                    db.mark_synced(tour_id, activity_id)
                    logger.info(f"  ✓ Recovered mapping: Komoot Tour {tour_id} → Strava Activity {activity_id}")
                    synced_count += 1
                else:
                    logger.debug(f"  Skip mapping: {tour_id} already in database")

        page += 1

    if latest_date:
        db.set_last_sync_time(latest_date)
        logger.info(f"Updated last sync time to {latest_date.isoformat()}")

    logger.info(f"=== Recovery Complete: {synced_count} missing references added to local database ===")

if __name__ == "__main__":
    main()
