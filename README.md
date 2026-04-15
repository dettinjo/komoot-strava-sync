# komoot-strava-sync

A self-hosted service that automatically syncs your completed **Komoot** activities to **Strava** — including the full GPX track, activity name, and description. Designed to run as a Docker container in [Coolify](https://coolify.io/) or any other Docker host.

---

## How it works

1. Every N minutes (default: 30) the service fetches your recently recorded Komoot tours.
2. For each tour not yet synced it downloads the GPX file from Komoot and uploads it to Strava.
3. The created Strava activity uses the same name, description, and sport type as the Komoot tour.
4. The activity is hidden from your followers' home feed (`hide_from_home=true`).
1. A local SQLite database tracks which tours have been synced so duplicates are never created.

---

## Limitations & Synced Data

**What is synced:**
- Tour name and description
- Mapped sport type
- Geospatial route (GPS track)
- Distance and elevation data
- Timestamps (start and end times)

**What is NOT synced (and cannot be synced):**
- Heart rate, power, and cadence data (Komoot's GPX exports do not include sensor metrics).
- Photos, media, highlights, or comments.
- Custom waypoints (they are baked into the route but don't appear as distinct points of interest in Strava).

Additionally, this setup relies on a **one-way sync** (Komoot → Strava). Recorded Strava activities are not synced back to Komoot.

---

## Privacy notice — important

**The Strava API does not support setting activity visibility to "Only You" programmatically.**

To ensure synced activities are only visible to you:

1. Open **Strava → Settings → Privacy Controls**
2. Set **Activities** to **"Only You"**
3. All API-uploaded activities will automatically inherit this setting

After reviewing each activity you can change its visibility to "Followers" or "Everyone" directly in the Strava app.

---

## Setup

### Prerequisites

- Docker + Docker Compose (or Coolify)
- A **Strava API application** — create one at <https://www.strava.com/settings/api>
  - Set **Authorization Callback Domain** to `localhost` (for the token helper script)
  - Required scopes: `activity:write,activity:read_all`
- Your **Komoot user ID** — visible in your profile URL:
  `https://www.komoot.com/user/123456789` → ID is `123456789`

### Step 1 — Configure environment

```bash
cp .env.template .env
# Edit .env and fill in KOMOOT_EMAIL, KOMOOT_PASSWORD, KOMOOT_USER_ID,
# STRAVA_CLIENT_ID, and STRAVA_CLIENT_SECRET
```

### Step 2 — Get Strava OAuth tokens (one-time, run on your local machine)

```bash
pip install requests          # only needed for the helper script
python scripts/get_token.py
```

The script opens a browser window for Strava authorization. After you approve, it prints three lines — paste them into your `.env`:

```
STRAVA_ACCESS_TOKEN=<long token>
STRAVA_REFRESH_TOKEN=<long token>
STRAVA_TOKEN_EXPIRES_AT=<unix timestamp>
```

The service refreshes the access token automatically from then on.

### Step 3 — Start the service

```bash
mkdir -p data
docker compose up -d
docker compose logs -f
```

On first startup the service syncs the last `INITIAL_SYNC_DAYS` (default: 30) days of activities, then polls every `SYNC_INTERVAL_MINUTES` (default: 30) minutes.

---

## Deploying on Coolify

1. Push this repository to GitHub/GitLab.
2. In Coolify create a new **Docker Compose** service pointing at the repo.
3. Mount `./data` as a persistent volume to `/data`.
4. Add all env vars from `.env` in the Coolify environment settings.
5. Deploy — no ports need to be exposed (the OAuth flow is done locally before deployment).

---

## Configuration reference

| Variable | Default | Description |
|---|---|---|
| `KOMOOT_EMAIL` | — | Komoot account email |
| `KOMOOT_PASSWORD` | — | Komoot account password |
| `KOMOOT_USER_ID` | — | Numeric Komoot user ID |
| `STRAVA_CLIENT_ID` | — | Strava API app Client ID |
| `STRAVA_CLIENT_SECRET` | — | Strava API app Client Secret |
| `STRAVA_ACCESS_TOKEN` | — | Initial access token (from `get_token.py`) |
| `STRAVA_REFRESH_TOKEN` | — | Initial refresh token (from `get_token.py`) |
| `STRAVA_TOKEN_EXPIRES_AT` | — | Token expiry unix timestamp (from `get_token.py`) |
| `SYNC_INTERVAL_MINUTES` | `30` | How often to poll Komoot for new activities |
| `INITIAL_SYNC_DAYS` | `30` | Days to look back on the very first run |
| `DATA_DIR` | `/data` | Directory for SQLite DB and token file |

---

## Sport type mapping

Komoot sport types are explicitly mapped to their Strava equivalents. The mapping covers all available primary Komoot sport types. The full mapping is maintained in [app/komoot.py](app/komoot.py). Any newly added or unknown Komoot types will gracefully fall back to `Workout` in Strava.

| Komoot | Strava |
|---|---|
| touringbicycle, road_cycling | Ride |
| e_touringbicycle | EBikeRide |
| mtb, mtb_easy, mtb_advanced | MountainBikeRide |
| e_mtb | EMountainBikeRide |
| hike, hiking | Hike |
| jogging, running | Run |
| trail_running | TrailRun |
| walking, nordic_walking | Walk |
| skitouring, skitour | BackcountrySki |
| snowshoe | Snowshoe |
| swimming | Swim |
| *(anything else)* | Workout |

---

## Duplicate prevention

Two independent mechanisms prevent the same activity from appearing twice in Strava:

1. **Local SQLite DB** — `data/sync.db` stores every `komoot_tour_id` that has been synced. Checked before each upload.
2. **Strava `external_id`** — each upload is tagged `komoot_<tourId>`. Strava rejects duplicate `external_id` values automatically.

---

## Troubleshooting

**"Strava tokens are missing"** — Run `python scripts/get_token.py` and add the output to `.env`.

**"Failed to download GPX for tour …"** — Komoot's unofficial API may have changed. Check that your email/password are correct and that the tour is fully recorded (not planned).

**Activity appears with wrong sport type** — The Komoot sport string for your activity isn't in the mapping table. Open `app/komoot.py` and add it to `SPORT_TYPE_MAP`.

**Activity is not private** — Ensure your Strava default activity privacy is set to "Only You" (Settings → Privacy Controls → Activities).
