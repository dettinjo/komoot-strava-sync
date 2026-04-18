# AI Handoff & Governance

Welcome! If you are an AI assistant taking over this project, read this document carefully before touching the codebase. It contains the workflow rules, architectural constraints, and the precise current project state.

---

## 📐 General Code Rules

1. **Python Compatibility**:
   - The runtime is **Python 3.9** (the system Python on the developer's Mac). All type hints must use `from __future__ import annotations` and `typing.Optional` / `typing.Union` — do NOT use the `X | Y` union syntax or `str | None` shorthand.
   - Every file starts with `from __future__ import annotations`.
   - Run formatting and linting using `ruff`. The backend is located in the `backend/` directory.
   - Explicit error handling only. No bare `except: pass`.

2. **Frameworks**:
   - Backend API: **FastAPI** (Async)
   - Database ORM: **SQLAlchemy 2.0** with `AsyncSession`. Never use synchronous queries.
   - Background Jobs: **ARQ** + **Redis**. Defer all network I/O (Komoot, Strava) to ARQ workers.
   - External HTTP: `httpx.AsyncClient` only. Never use synchronous `requests`.
   - Settings: **pydantic-settings** (`BaseSettings`) loaded from `.env`. Never read `os.environ` directly in route handlers or services.

3. **Architectural Constraints**:
   - The root `app/` directory contains the **legacy synchronous scripts**. They are frozen — do not modify or import from them. The modern SaaS backend lives entirely inside `backend/app/`.
   - Database interactions use dependency injection: `db: AsyncSession = Depends(get_db)`.
   - Credentials (Komoot password, Strava tokens) are **always stored encrypted** (AES-256 Fernet). Decrypt only in-memory when needed inside a job.

---

## 🔄 AI Handoff Workflow

1. Read `backend/CLAUDE.md` — compact architecture reference with code patterns.
2. Read the **Current Project State** section below to know exactly where to pick up.
3. Run `cd backend && python -m pytest tests/ -v` to confirm the green baseline before making changes.
4. Update this **Current State** section before concluding your session.

---

## 📁 Backend File Map

```
backend/
├── app/
│   ├── core/
│   │   ├── config.py           # pydantic-settings: all env vars declared here
│   │   ├── security.py         # JWT encode/decode, Fernet encrypt/decrypt, API key hashing
│   │   └── rate_limit.py       # RateLimitGuard wrapping Strava 15-min + daily limits via Redis
│   ├── db/
│   │   ├── session.py          # engine + AsyncSessionLocal + get_db() dependency
│   │   └── models/
│   │       ├── user.py         # User, StravaApp, StravaToken
│   │       ├── sync.py         # SyncedActivity, UserSyncState, SyncRule, JobAuditLog
│   │       └── subscription.py # Subscription, ApiKey, WebhookSubscription
│   ├── api/
│   │   ├── deps.py             # get_current_user, require_tier, get_current_api_key_user
│   │   └── v1/
│   │       ├── router.py       # Mounts all sub-routers
│   │       ├── auth.py         # Strava OAuth2 + Komoot vault setup
│   │       ├── sync.py         # POST /trigger, POST /rebuild-history
│   │       ├── activities.py   # GET /activities (paginated sync history)
│   │       ├── rules.py        # GET+POST /rules (Pro tier)
│   │       ├── api_keys.py     # GET+POST /api-keys (Pro tier)
│   │       ├── billing.py      # POST /billing/checkout + /billing/portal
│   │       └── webhooks.py     # POST+GET /webhooks/stripe + /webhooks/strava
│   ├── services/
│   │   ├── komoot.py           # KomootClient: get_tours(), download_gpx()
│   │   ├── strava.py           # StravaClient: upload_gpx(), poll_upload(), update_activity(), get_activities()
│   │   └── sync.py             # SyncService: sync_komoot_to_strava() with rule evaluation
│   ├── jobs/
│   │   ├── sync_jobs.py        # ARQ jobs: poll_komoot_user, process_strava_activity, komoot_poll_scheduler
│   │   └── worker.py           # ARQ WorkerSettings
│   └── main.py                 # FastAPI app factory with lifespan (ARQ pool init)
├── tests/
│   ├── conftest.py             # Env bootstrap + async_client fixture (no real infra needed)
│   └── api/
│       ├── test_activities.py
│       ├── test_api_keys.py
│       ├── test_auth.py
│       ├── test_billing.py
│       ├── test_rules.py       # NEW: CRUD tests for sync rules
│       ├── test_sync.py        # NEW: Rule-evaluation unit test (mocks rate_limit_guard)
│       └── test_webhooks.py
├── scripts/
│   └── live_test.py            # Standalone E2E script using real credentials (sqlite in-memory)
├── alembic/                    # DB migration files
└── CLAUDE.md                   # Compact architecture guide for AI agents
```

---

## 📅 Current Project State

**Last Updated**: 2026-04-18

**Backend Status**: ⚠️ **Substantially implemented, but docs still lag in places**. The backend has real route, service, and worker code, and the current local baseline is green. The main remaining risk is documentation drift and deeper integration coverage rather than obvious route gaps.

### Recent Fixes (2026-04-17)

- Added `CODEX.md`, a repo-local Codex skill, and a `Makefile` so Codex can follow a consistent workflow similar to the existing Claude setup.
- Rewrote `backend/alembic/versions/001_initial_schema.py` so a fresh database schema now matches the current ORM models much more closely.
- Strava OAuth callback now stores `access_token` and `refresh_token` encrypted with Fernet instead of raw `.encode()` bytes.
- Added automatic Strava token refresh in the worker path before Komoot→Strava sync jobs and before reverse-sync webhook processing.
- Added a compatibility read path for legacy raw token bytes so older rows can still be refreshed and normalized.
- Strava webhook processing now resolves the local user by `strava_tokens.strava_athlete_id` instead of treating `owner_id` as a local user UUID.
- Reverse-sync activity fetch now goes through `RateLimitGuard.call()` using the normal Strava client rather than an ad hoc direct HTTP request.
- Added tests covering encrypted token persistence and token refresh behavior.

### Recent Verification (2026-04-18)

- Installed the missing local Python test dependencies needed to run the backend checks in this environment (`pytest`, `alembic`, `aiosqlite`, and related backend requirements).
- `cd backend && python -m pytest tests/ -v` now passes: **12 passed**.
- The rewritten initial migration was validated against a clean temporary PostgreSQL 16 container using `python -m alembic upgrade head`.
- Post-migration sanity check confirmed the expected tables plus `alembic_version=001`.
- Cleaned up repo setup drift: root `README.md` now describes the current backend-centric state, `.env.saas.template` and `.env.selfhosted.template` were added, `backend/requirements.txt` now includes `aiosqlite`, and `docker-compose.yml` no longer references the missing `frontend/` service.
- `docker compose config` succeeds against the updated backend-only compose file when a real `.env.saas` file exists. In this repo, the existing root `.env` contains a password with `$`, which still causes interpolation warnings in Docker Compose unless values are escaped or Compose is pointed at a different env file.
- `Makefile` now uses `docker compose --env-file .env.saas` for backend dev commands, and the env templates now include `POSTGRES_PASSWORD`. `.gitignore` was updated so the new env template files remain tracked.
- Added the next batch of product-facing API endpoints: `GET /sync/status`, `GET /activities/{id}`, `PUT/DELETE /rules/{id}`, `DELETE /api-keys/{id}`, and disconnect endpoints for Strava and Komoot.
- `cd backend && python -m pytest tests/ -v` now passes with the expanded route coverage: **17 passed**.
- Added account auth endpoints for `POST /auth/register`, `POST /auth/login`, and `POST /auth/refresh`, plus `GET /billing/subscription`.
- `cd backend && python -m pytest tests/ -v` now passes with the expanded auth/billing route coverage: **19 passed**.
- Added `GET /activities/{id}/gpx`, which downloads GPX on demand from Komoot for user-owned synced activities that still have a `komoot_tour_id` and valid stored Komoot credentials.
- `cd backend && python -m pytest tests/ -v` now passes with GPX download coverage: **20 passed**.

---

### ✅ Fully Implemented Features

#### 1. Authentication & Security (`auth.py`, `security.py`, `deps.py`)
- **Account auth**: `POST /auth/register` creates a user plus a default free subscription and returns a bearer token. `POST /auth/login` verifies email/password and returns a bearer token. `POST /auth/refresh` issues a fresh bearer token for an authenticated user.
- **Strava OAuth2 flow**: `GET /auth/strava/login` redirects to Strava; callback at `POST /auth/strava/callback` exchanges code for tokens and stores the resulting Strava tokens encrypted in `strava_tokens`.
- **Komoot Vault**: `POST /auth/komoot` accepts `{email, password}` and stores them as AES-256 Fernet ciphertext in the DB (`komoot_email_encrypted`, `komoot_password_encrypted`). The plaintext is never persisted.
- **Disconnect endpoints**: `DELETE /auth/strava/disconnect` removes the stored Strava token, and `DELETE /auth/komoot/disconnect` clears stored Komoot credentials and disables Komoot→Strava sync.
- **JWT auth**: All protected routes use `Depends(deps.get_current_user)` which validates the Bearer token and loads the `User` model.
- **Tier gating**: `Depends(deps.require_tier("pro"))` queries `Subscription` and raises HTTP 402 if the user's tier is insufficient.
- **API Key auth**: `X-API-Key` header validated by `get_current_api_key_user` — keys are stored as SHA-256 hashes, never in plaintext.

#### 2. Komoot → Strava Sync (Full Pipeline)
- `KomootClient.get_tours(since)` paginates the Komoot v007 API, filters by date, maps sport types to Strava equivalents via `SPORT_TYPE_MAP` (~25 types supported).
- `KomootClient.download_gpx(tour_id)` fetches the GPX bytes.
- `SyncService.sync_komoot_to_strava()` orchestrates:
  1. Loads/creates `UserSyncState` for the user.
  2. **Fetches active `SyncRule` rows** for the user and evaluates them before each tour. If a rule's `conditions.sport` matches the tour sport and `actions.sync_to == "None"`, the tour is **skipped**.
  3. Checks `SyncedActivity` for duplicates (idempotent by `komoot_tour_id`).
  4. Downloads GPX and uploads to Strava via `StravaClient`, wrapped in `rate_limit_guard.call()`.
  5. Polls upload status until `activity_id` is available.
  6. Sets `hide_from_home` on the Strava activity.
  7. Writes a `SyncedActivity` record with full metadata (name, sport, distance, elevation, start time).
  8. Updates `UserSyncState` timestamps and counts.

#### 3. Strava → Komoot Reverse Sync (Scaffolded — Komoot API limitation)
- Strava pushes activity events to `POST /webhooks/strava` (registered via Strava Webhook API).
- The webhook enqueues `process_strava_activity(athlete_id, activity_id)` to ARQ and the worker resolves the user through `strava_tokens.strava_athlete_id`.
- The job fetches the full Strava activity JSON, creates a `SyncedActivity` record with `sync_direction="strava_to_komoot"` and `sync_status="pending"`.
- **Why pending**: Komoot does not expose a public GPX upload API. The record is persisted and ready — when a Komoot upload endpoint is discovered (reverse-engineered or official), plug it into the `process_strava_activity` job after the metadata fetch.

#### 4. Rebuild History / Sync from External (`POST /sync/rebuild-history`)
- Crawls the authenticated user's Strava activity history (`GET /athlete/activities`).
- Identifies activities with `external_id` starting with `komoot_` (the tag the sync engine sets on every upload).
- Backfills matching `SyncedActivity` rows so the sync engine treats them as already-synced on the next run.
- Safe to call multiple times (upsert-style: existing records are skipped).
- Accepts `lookback_days` query param (default 180, max 730).

#### 5. Activity History Feed (`GET /activities`, `GET /activities/{id}`, `GET /activities/{id}/gpx`)
- Paginated endpoint returning `SyncedActivity` rows for the authenticated user.
- Detail endpoint returning a single user-scoped `SyncedActivity` including duration/conflict fields when present.
- GPX download endpoint streams `application/gpx+xml` directly from Komoot on demand for synced activities tied to a Komoot tour.
- GPX download requires the current user to still have Komoot credentials stored; otherwise it returns HTTP 409.
- Returns: `id`, `komoot_tour_id`, `strava_activity_id`, `sync_direction`, `sync_status`, `activity_name`, `sport_type`, `distance_m`, `elevation_up_m`, `started_at`, `synced_at`.
- Status values: `pending`, `processing`, `completed`, `failed`, `conflict`.

#### 6. Sync Status (`GET /api/v1/sync/status`)
- Returns connection flags, enabled sync directions, latest `UserSyncState` fields, and the user's most recent synced activity.
- This is the main lightweight dashboard/status endpoint for the current backend.

#### 7. Individual Sync Rules (`GET /api/v1/rules`, `POST /api/v1/rules`, `PUT /api/v1/rules/{id}`, `DELETE /api/v1/rules/{id}`)
- **Requires Pro tier**.
- Rules are JSON objects with `conditions` (e.g. `{"sport": "E-Bike"}`) and `actions` (e.g. `{"sync_to": "None"}`).
- Up to **15 rules per user**, evaluated in `rule_order` order.
- The `SyncService` evaluates rules at runtime — sport-type matching is case-insensitive.
- Supported `direction` values: `komoot_to_strava`, `strava_to_komoot`, `both`.

#### 8. Developer API Keys (`GET /api/v1/api-keys`, `POST /api/v1/api-keys`, `DELETE /api/v1/api-keys/{id}`)
- **Requires Pro tier**.
- Generates a `kss_`-prefixed raw key returned **once** at creation time.
- Stores only the SHA-256 hash and a `key_prefix` (first 8 chars + `...`) for display.
- Limit of 5 active keys per user.
- Delete is implemented as revoke: it sets `revoked_at` rather than removing the DB row.

#### 9. Billing (Stripe)
- `GET /billing/subscription` returns the current subscription snapshot for the authenticated user, defaulting to a synthetic free-tier view when no subscription row exists.
- `POST /billing/checkout` creates a Stripe Checkout Session for `pro` or `business` tier; returns `{url}` to redirect the user.
- `POST /billing/portal` creates a Stripe Billing Portal session for managing existing subscriptions.
- `POST /webhooks/stripe` handles `checkout.session.completed`, `customer.subscription.deleted`, and `customer.subscription.updated` events to update the local `Subscription` table.

#### 10. ARQ Background Workers
- `poll_komoot_user(ctx, user_id)`: Loads the user + token, refreshes the Strava token if it is near expiry, instantiates clients, runs `SyncService.sync_komoot_to_strava()`.
- `process_strava_activity(ctx, athlete_id, activity_id)`: Resolves the user from the Strava athlete id, refreshes the token if needed, and records inbound Strava activities for future reverse sync.
- `komoot_poll_scheduler(ctx)`: Cron job that queries users with `next_komoot_poll_at <= now` and enqueues `poll_komoot_user` for each.

#### 11. Rate Limiting (`core/rate_limit.py`)
- `RateLimitGuard` tracks per-`strava_app_id` request counts in Redis.
- Hard limits: 100 req / 15 min, 1000 req / day.
- Pro users get elevated limits.
- All Strava API calls in `SyncService` pass through `rate_limit_guard.call()`.

---

### 📋 DB Models Summary

| Model | Table | Key columns |
|---|---|---|
| `User` | `users` | `id (UUID)`, `email`, `komoot_email_encrypted`, `komoot_password_encrypted`, `komoot_user_id`, `sync_komoot_to_strava`, `hide_from_home_default` |
| `StravaApp` | `strava_apps` | `client_id`, `client_secret (bytes)`, `display_name`, `daily_requests` |
| `StravaToken` | `strava_tokens` | `user_id→users`, `strava_app_id→strava_apps`, `access_token (bytes)`, `refresh_token (bytes)`, `expires_at` |
| `Subscription` | `subscriptions` | `user_id→users`, `tier (free/pro/business)`, `status`, `stripe_customer_id`, `stripe_subscription_id` |
| `ApiKey` | `api_keys` | `user_id→users`, `key_hash`, `key_prefix`, `name`, `revoked_at`, `expires_at` |
| `SyncedActivity` | `synced_activities` | `user_id→users`, `komoot_tour_id`, `strava_activity_id`, `sync_direction`, `sync_status`, `activity_name`, `sport_type`, `distance_m`, `elevation_up_m`, `started_at`, `duration_seconds` |
| `UserSyncState` | `user_sync_state` | `user_id→users (PK)`, `last_komoot_sync_at`, `last_successful_sync_at`, `total_synced_count`, `last_error` |
| `SyncRule` | `sync_rules` | `user_id→users`, `name`, `direction`, `conditions (JSON)`, `actions (JSON)`, `rule_order`, `is_active` |

---

### 🧪 Test Status

`python -m pytest tests/ -v` passes in the current local Python 3.11 environment after installing backend dependencies. Current result: **20 passed**.

| Test file | What it covers |
|---|---|
| `test_activities.py` | Activity list, activity detail, and GPX download endpoints |
| `test_api_keys.py` | Create key, list keys, revoke key |
| `test_auth.py` | Strava login URL generation, Komoot credential storage |
| `test_auth_accounts.py` | Register, login, and refresh token flows |
| `test_auth_disconnect.py` | Disconnecting Komoot and Strava integrations |
| `test_sync_jobs.py` | Refreshes expiring Strava tokens before workers use them |
| `test_billing.py` | Subscription status and Stripe Checkout session creation |
| `test_rules.py` | Create/list/update/delete sync rules |
| `test_sync.py` | Rule engine blocks E-Bike tour, passes Running tour |
| `test_sync_status.py` | Sync status aggregate endpoint |
| `test_webhooks.py` | Stripe bad-signature rejection, Strava verify challenge, Strava activity push |

**Key `conftest.py` pattern**: env vars are set via `os.environ` before any app import. `get_current_user` is overridden per test via `app.dependency_overrides`. The `FakeDB` class dispatches `scalar_one_or_none()` / `scalars().all()` based on `str(stmt).lower()` content.

---

### 🚩 Known Limitations / Next Steps

| Area | Status | Notes |
|---|---|---|
| **Strava → Komoot upload** | ⏸ Blocked | Komoot has no public upload API. Reverse-engineered mobile session is the only path. DB record is persisted and waiting. |
| **Alembic migrations** | ✅ Initial migration verified on clean Postgres | The initial migration was rewritten and successfully applied to a clean PostgreSQL 16 container. If schema changes continue, the next step is comparing ORM metadata to DB state after future edits. |
| **Token refresh** | ✅ Implemented in worker paths | `poll_komoot_user()` and `process_strava_activity()` now refresh near-expiry Strava tokens before making API calls. The API layer still does not expose a dedicated token maintenance endpoint, which is fine for current behavior. |
| **Docs drift** | ⚠️ Ongoing | `PROJECT.md`, `README.md`, and some planning notes still contain stale assumptions. Validate against code before trusting written docs. |
| **Docker env handling** | ⚠️ Mostly fixed for normal dev flow | `make dev` now uses `--env-file .env.saas`, which avoids depending on the legacy root `.env`. Remaining cleanup is optional hardening around direct raw `docker compose` usage in this repo if contributors still invoke it manually. |
| **Frontend** | ❌ Not started | See `frontend_ui_prompt.md` in the project root for a complete spec. React/Vite. Connects to `/api/v1/*`. |
| **Komoot → Strava idempotency** | ✅ Robust | `SyncedActivity` has `UNIQUE (user_id, komoot_tour_id)`. Strava also rejects duplicate `external_id` values natively. |
| **Docker Compose** | ✅ Present | `docker-compose.saas.yml` runs `api`, `worker`, `postgres`, `redis`. Backend requires these services to be running for the full sync pipeline. |

---

### 🔑 Required Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://...` |
| `REDIS_URL` | ✅ | `redis://redis:6379` |
| `SECRET_KEY` | ✅ | JWT signing key |
| `KOMOOT_ENCRYPTION_KEY` | ✅ | Fernet key for Komoot credential encryption |
| `STRAVA_CLIENT_ID` | ✅ | Strava developer app |
| `STRAVA_CLIENT_SECRET` | ✅ | Strava developer app |
| `STRIPE_SECRET_KEY` | Optional | Billing |
| `STRIPE_WEBHOOK_SECRET` | Optional | Billing |
| `STRIPE_PRICE_PRO` | Optional | Price ID for Pro tier |
| `STRIPE_PRICE_BUSINESS` | Optional | Price ID for Business tier |
| `STRAVA_WEBHOOK_VERIFY_TOKEN` | Optional | Strava webhook challenge |

Test credentials for development are saved in the root `.env` file.
