# komoot-strava-sync — Project Overview & AI Handoff

> **Living document.** Read this first when picking up work with any AI tool (Claude Code, Gemini Antigravity, OpenAI Codex). Update it at the end of every session. Last updated: 2026-04-18.

---

## 🎯 Project Goal

Build a **dual-mode platform** that automatically syncs Komoot activities to Strava:

1. **Legacy standalone tool** (`/legacy`) — single-user, single Docker container, MIT open source, zero infra. **Feature complete, frozen.** Original `/app` directory, renamed to `/legacy`.
2. **SaaS backend** (`/backend`) — multi-tenant FastAPI service with PostgreSQL, Redis, Stripe subscriptions, and feature-gating by tier. **Substantially implemented.**
3. **Frontend** (`/frontend`) — Next.js dashboard. **Not yet started.**

Both the SaaS and a self-hosted variant can run the same frontend dashboard. A self-hosted user gets the full stack with a license key for premium features (architecture scaffolded, not yet wired).

---

## 🗺️ Architecture Overview

```
komoot-strava-sync/
├── legacy/          ← Old standalone single-user tool (frozen, MIT)
├── backend/         ← SaaS multi-tenant API (FastAPI, Postgres, Redis, ARQ)
├── frontend/        ← Next.js dashboard (NOT STARTED)
├── docs/            ← Setup guides
├── .claude/         ← Claude Code worktree directory
├── .codex/          ← OpenAI Codex config
├── docker-compose.yml               ← Backend SaaS dev stack
├── docker-compose.production.yml    ← Production variant
├── .env.saas.template               ← Cloud SaaS env vars template
├── .env.selfhosted.template         ← Self-hosted env vars template
├── Makefile                         ← Dev workflow commands
├── CLAUDE.md                        ← Claude Code quick reference
├── CODEX.md                         ← OpenAI Codex quick reference
└── PROJECT_OVERVIEW.md              ← THIS FILE — source of truth
```

### Backend Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI (async) + Uvicorn |
| ORM | SQLAlchemy 2.0 async + asyncpg |
| Database | PostgreSQL 16 |
| Migrations | Alembic |
| Job queue / cache | Redis 7 + ARQ |
| Auth | JWT (python-jose) + API keys (SHA-256 hash) |
| Encryption | Fernet (cryptography) — Komoot creds + Strava tokens |
| Payments | Stripe (Checkout + webhooks) |
| HTTP clients | httpx (async) |
| Config | pydantic-settings BaseSettings |
| Testing | pytest + pytest-asyncio + respx + aiosqlite (in-memory SQLite) |
| Linting | ruff (line-length 100, Python 3.12 target) |

---

## 📁 Backend File Map

```
backend/
├── app/
│   ├── core/
│   │   ├── config.py           # pydantic-settings: all env vars declared here
│   │   ├── security.py         # JWT encode/decode, Fernet encrypt/decrypt, API key hashing
│   │   └── rate_limit.py       # RateLimitGuard — wraps all outbound Strava calls via Redis
│   ├── db/
│   │   ├── session.py          # engine + AsyncSessionLocal + get_db() dependency
│   │   └── models/
│   │       ├── user.py         # User, StravaApp, StravaToken
│   │       ├── sync.py         # SyncedActivity, UserSyncState, SyncRule, JobAuditLog
│   │       └── subscription.py # Subscription, ApiKey, WebhookSubscription, NotificationSettings, LicenseCache
│   ├── api/
│   │   ├── deps.py             # get_current_user, require_tier, get_current_api_key_user
│   │   └── v1/
│   │       ├── router.py       # Mounts all sub-routers under /api/v1
│   │       ├── auth.py         # Register, login, refresh, Strava OAuth2, Komoot vault, disconnect
│   │       ├── sync.py         # POST /trigger, GET /status, POST /rebuild-history
│   │       ├── activities.py   # GET /activities (paginated), GET /activities/{id}, GET /activities/{id}/gpx
│   │       ├── rules.py        # CRUD /rules (Pro tier, max 15)
│   │       ├── api_keys.py     # CRUD /api-keys (Pro tier, max 5)
│   │       ├── billing.py      # GET /subscription, POST /checkout, POST /portal
│   │       └── webhooks.py     # POST+GET /webhooks/strava + POST /webhooks/stripe
│   ├── services/
│   │   ├── komoot.py           # KomootClient: get_tours(), download_gpx()
│   │   ├── strava.py           # StravaClient: upload_gpx(), poll_upload(), update_activity(), get_activities()
│   │   └── sync.py             # SyncService: sync_komoot_to_strava() with rule evaluation + rate limiting
│   ├── jobs/
│   │   ├── sync_jobs.py        # ARQ jobs: poll_komoot_user, process_strava_activity, komoot_poll_scheduler
│   │   └── worker.py           # ARQ WorkerSettings (max 10 concurrent, 600s timeout, 5-min cron)
│   └── main.py                 # FastAPI app factory with lifespan (ARQ pool init/teardown)
├── tests/
│   ├── conftest.py             # Env bootstrap + async_client fixture (SQLite in-memory, no real infra)
│   └── api/
│       ├── test_activities.py  # Activity list, detail, GPX download
│       ├── test_api_keys.py    # Create, list, revoke API keys
│       ├── test_auth.py        # Strava OAuth URL, Komoot credential storage
│       ├── test_auth_accounts.py # Register, login, refresh token
│       ├── test_auth_disconnect.py # Disconnect Komoot + Strava
│       ├── test_billing.py     # Subscription status, Stripe Checkout session
│       ├── test_rules.py       # Create/list/update/delete sync rules
│       ├── test_sync.py        # Rule engine (blocks E-Bike, passes Running)
│       ├── test_sync_jobs.py   # Token refresh in worker path
│       ├── test_sync_status.py # Sync status endpoint
│       └── test_webhooks.py    # Stripe bad-sig, Strava challenge, Strava activity push
├── scripts/
│   └── live_test.py            # Standalone E2E script with real credentials
├── alembic/
│   └── versions/001_initial_schema.py  # Validated against clean PostgreSQL 16
├── requirements.txt
├── pyproject.toml              # ruff config + pytest asyncio_mode=auto
├── Dockerfile
└── CLAUDE.md                   # Compact AI reference for Claude Code
```

---

## ✅ What Is Implemented

### Authentication & Security
- `POST /auth/register` — creates User + default free Subscription, returns JWT
- `POST /auth/login` — bcrypt validation, returns JWT
- `POST /auth/refresh` — returns fresh JWT for authenticated user
- `GET /auth/strava/login` — redirects to Strava OAuth URL
- `POST /auth/strava/callback` — exchanges code, stores tokens encrypted (Fernet), sets `strava_athlete_id`
- `POST /auth/komoot` — stores encrypted Komoot email+password (never plaintext)
- `DELETE /auth/strava/disconnect` — removes StravaToken
- `DELETE /auth/komoot/disconnect` — clears Komoot creds, disables sync
- All protected routes use `Depends(get_current_user)` (Bearer JWT)
- Tier gating: `Depends(require_tier("pro"))` → HTTP 402 if insufficient
- API key auth: `X-API-Key` header, SHA-256 hash stored, plaintext returned only once

### Komoot → Strava Sync (Full Pipeline)
- `KomootClient.get_tours(since)` — paginates Komoot v007 API, maps ~44 sport types to Strava equivalents
- `KomootClient.download_gpx(tour_id)` — fetches GPX bytes from Komoot
- `SyncService.sync_komoot_to_strava()` orchestrates:
  1. Load/create `UserSyncState` (cursor tracking, lookback: 30d first run / since last sync)
  2. Evaluate active `SyncRule` rows (conditions: sport, distance, elevation; actions: skip, etc.)
  3. Skip duplicates by `komoot_tour_id` (unique constraint in `synced_activities`)
  4. Download GPX → upload to Strava (through `RateLimitGuard`)
  5. Poll upload status until `activity_id` available
  6. Set `hide_from_home` per user preference
  7. Write `SyncedActivity` record (name, sport, distance, elevation, start time)
  8. Update `UserSyncState` timestamps and counts

### Strava → Komoot Reverse Sync (Scaffolded — blocked by Komoot API)
- Strava pushes activity events to `POST /webhooks/strava`
- Worker resolves user via `strava_tokens.strava_athlete_id`
- Fetches activity metadata from Strava API (through `RateLimitGuard`)
- Creates `SyncedActivity` with `sync_status="pending"` and `sync_direction="strava_to_komoot"`
- **Blocked**: Komoot has no public GPX upload API. Records ready — plug in upload when endpoint discovered.

### Other Sync Features
- `POST /sync/trigger` — manual sync trigger (enqueues ARQ job)
- `GET /sync/status` — connection flags, last sync times, last error, latest activity
- `POST /sync/rebuild-history` — crawls Strava history, backfills `SyncedActivity` for `external_id=komoot_*`

### Activity History Feed
- `GET /activities` — paginated `SyncedActivity` list (filter by direction/status)
- `GET /activities/{id}` — detail with conflict info
- `GET /activities/{id}/gpx` — streams GPX from Komoot on demand (requires active Komoot creds)

### Sync Rules Engine (Pro tier)
- `GET/POST/PUT/DELETE /rules` — CRUD, max 15 per user, evaluated in `rule_order`
- Conditions: `sport_type`, `distance_km`, `elevation_m`, `duration_min`, `name_contains`
- Actions: `skip`, `set_sport_type`, `name_template`, `append_description`, `set_hide_from_home`
- First match wins, case-insensitive sport matching

### Developer API Keys (Pro tier)
- `GET/POST/DELETE /api-keys` — max 5 per user, SHA-256 hash stored, raw key returned once
- Revoke sets `revoked_at` (soft delete, preserved for audit)

### Billing (Stripe)
- `GET /billing/subscription` — subscription snapshot (tier, status, period, activities synced)
- `POST /billing/checkout` — creates Stripe Checkout Session, returns `{url}`
- `POST /billing/portal` — creates Stripe Customer Portal session
- `POST /webhooks/stripe` — handles `checkout.session.completed`, `customer.subscription.{deleted,updated}`

### Background Workers (ARQ + Redis)
- `komoot_poll_scheduler` — cron every 5 min, queries users due for polling, enqueues `poll_komoot_user`
- `poll_komoot_user(user_id)` — decrypts creds, refreshes Strava token if near expiry, runs sync pipeline
- `process_strava_activity(athlete_id, activity_id)` — records inbound Strava activities for reverse sync

### Rate Limiting (`core/rate_limit.py`)
- `RateLimitGuard` — ALL outbound Strava API calls MUST pass through `rate_limit_guard.call(app_id, tier, fn, ...)`
- Redis keys: `strava:{app_id}:rl:15min:{window}` (900s TTL), `strava:{app_id}:rl:daily:{date}` (86400s TTL)
- Limits: 90 req/15 min (headroom), 950 req/day (headroom)
- Free tier suspended when shared daily usage > 800 (reserves 150 for Pro users)
- Tier priorities: free=5, pro=10, business=15

### Database Models (all in Alembic migration `001`)
| Model | Table | Key columns |
|---|---|---|
| `User` | `users` | `id (UUID)`, `email`, `komoot_*_encrypted`, `sync_komoot_to_strava`, `next_komoot_poll_at` |
| `StravaApp` | `strava_apps` | `client_id`, `client_secret (bytes)`, `daily_requests`, `daily_reset_at` |
| `StravaToken` | `strava_tokens` | `user_id`, `strava_athlete_id` (for webhook routing), `access_token (bytes)`, `refresh_token (bytes)`, `expires_at` |
| `Subscription` | `subscriptions` | `user_id`, `tier (free/pro/business)`, `status`, `stripe_customer_id`, `activities_synced_this_period` |
| `ApiKey` | `api_keys` | `user_id`, `key_hash`, `key_prefix`, `revoked_at`, `expires_at` |
| `SyncedActivity` | `synced_activities` | `user_id`, `komoot_tour_id`, `strava_activity_id`, `sync_direction`, `sync_status`, metadata |
| `UserSyncState` | `user_sync_state` | `user_id (PK)`, `last_komoot_sync_at`, `last_successful_sync_at`, `total_synced_count`, `last_error` |
| `SyncRule` | `sync_rules` | `user_id`, `name`, `direction`, `conditions (JSON)`, `actions (JSON)`, `rule_order` |
| `JobAuditLog` | `job_audit_log` | `job_id`, `job_type`, `user_id`, `status`, `enqueued_at`, `payload (JSON)` |
| `WebhookSubscription` | `webhook_subscriptions` | `user_id`, `platform`, `endpoint_url`, `is_active` |
| `NotificationSettings` | `notification_settings` | `user_id`, `channel`, `event_type`, `is_enabled` |
| `LicenseCache` | `license_cache` | `user_id`, `tier`, `max_users`, `features (JSON)`, `grace_until` |

### Tests (20 passing)
Run with: `cd backend && python -m pytest tests/ -v`
- Uses in-memory SQLite (`aiosqlite`), no real infra needed
- `FakeDB` pattern in `conftest.py` dispatches on SQL string content
- All 11 test files pass clean on current codebase

---

## ❌ What Is NOT Implemented

| Component | Status | Notes |
|-----------|--------|-------|
| **Frontend** | ❌ Not started | Next.js dashboard (spec in old `frontend_ui_prompt.md`) |
| **Strava → Komoot upload** | ⏸ Blocked | Komoot has no public GPX upload API. DB record stored and waiting. |
| **Multi-app Strava pooling** | ⚠️ Architecture only | `strava_apps` table exists; routing logic not implemented |
| **License server / self-hosted gating** | ⚠️ Schema only | `license_cache` table exists; not wired to API tier checks |
| **Komoot exponential backoff** | ⚠️ Missing | Should retry with backoff on 429/5xx from Komoot |
| **Docker Compose `$` escape** | ⚠️ Minor | Passwords with `$` in `.env.saas` cause interpolation warnings |
| **Activity quota enforcement** | ⚠️ Partial | `activities_synced_this_period` tracked but not enforced as hard limit |
| **Notification delivery** | ❌ | `NotificationSettings` model exists, no email/push sending implemented |
| **Webhook delivery** | ❌ | `WebhookSubscription` model exists, no outbound delivery implemented |
| **Admin endpoints** | ❌ | No `/admin` routes (user management, app health, Strava app pool management) |
| **Token key rotation** | ⚠️ | `komoot_key_version` field exists, rotation logic not implemented |

---

## 🔑 API Constraints & Limits

### Strava API
- **Rate limit**: 100 req/15 min, 1000 req/day **per registered app** (shared across ALL cloud users)
- **Per sync cost**: ~4-5 API calls (upload + 2-3 polls + update_activity + amortized token refresh)
- **Capacity**: ~200-210 syncs/day safely per Strava app → supports ~150-200 active users before multi-app pooling required
- **Scaling path**: `strava_apps` table supports multiple apps; `RateLimitGuard` is app-scoped. Routing logic needed.
- **Free tier suspension**: When daily usage > 800, free-tier calls blocked (reserves 150 for Pro)
- **Webhooks**: Strava pushes activity events to our endpoint → near-realtime sync for Pro users

### Komoot API
- **Unofficial**: `https://www.komoot.de/api/v007` — reverse-engineered, violates ToS
- **Auth**: HTTP Basic (email + password) — no OAuth, no API keys
- **No webhooks**: Polling only, must poll for new tours
- **No upload API**: Cannot push GPX to Komoot (blocks reverse sync)
- **IP-block risk at scale**: 100 users/30-min poll = ~3 req/min (safe); 500+ users = potential flagging
- **Fragility**: API can change without notice — must fail gracefully with retry
- **Self-hosters unaffected**: Each self-hosted instance polls from its own IP

### Current Implementation vs. API Limits
| Constraint | Status |
|-----------|--------|
| All Strava calls through `RateLimitGuard` | ✅ Enforced |
| Free tier suspended at 800/day shared | ✅ Implemented |
| Komoot error handling + retry | ⚠️ Basic try/catch, no exponential backoff |
| Komoot ToS risk documented | ✅ Documented in PROJECT.md and CLAUDE.md |
| Multi-app Strava pooling for scale | ⚠️ Architecture only, not routed |

---

## 💰 Business Model

### Tiers
| Feature | Free | Pro ($3.49/mo or $29/yr) |
|---------|------|--------------------------|
| Sync direction | Komoot → Strava | Komoot → Strava + (Strava → Komoot when available) |
| Sync interval | ~2 hours (batch) | ~10 minutes (near-realtime via webhook) |
| History lookback | 30 days | 12 months |
| Sync rules | 1 | 5 |
| API key access | ❌ | ✅ |
| GPX on-demand download | ❌ | ✅ |
| Email support | ❌ | ✅ |

### Self-Hosted (AGPL v3)
- Full stack free (bring your own Strava app + PostgreSQL + Redis)
- License key unlocks Pro features for self-hosters (architecture planned, not implemented)
- No IP-block risk from Komoot (each install uses own IP)

### Economics (target: micro-SaaS)
- Break-even: ~7 paying users at $29/yr
- 50 users → ~€105/mo profit, 200 → ~€445/mo, 1000 → ~€2,320/mo
- Strava shared rate limit is the key scaling constraint → multi-app pooling needed at ~200 users

---

## 🏗️ Suitability Analysis

### Self-Hosting
✅ **Well-suited.** Docker Compose brings up the full stack in one command. AGPL license requires source disclosure. License key gating for premium features is architecturally planned (schema exists). Self-hosters avoid the shared Strava rate limit issue.

### Cloud SaaS (Multi-User)
✅ **Architecture is correct.** Multi-tenant UUID-scoped data, encrypted credentials, ARQ job queue, Redis rate limiting. Strava shared rate limit is the primary scaling constraint — solvable by adding more Strava app registrations.

⚠️ **Current bottleneck**: One Strava app handles all cloud users. At ~200 active users syncing daily, the 1000 req/day limit will be hit. Multi-app routing logic needs implementation before public launch.

### Switching Between AI Tools
The project is set up with separate config files for each AI tool:
- `CLAUDE.md` — Claude Code quick reference (coding rules, commands, constraints)
- `CODEX.md` — OpenAI Codex quick reference
- `.claude/` — Claude Code worktrees, hooks, settings
- `.codex/` — Codex configuration
- `PROJECT_OVERVIEW.md` (THIS FILE) — source of truth for all AIs

**Recommended handoff protocol:**
1. Read `PROJECT_OVERVIEW.md` first
2. Read the AI-specific config (`CLAUDE.md` or `CODEX.md`)
3. Run `cd backend && python -m pytest tests/ -v` to confirm green baseline
4. Update `PROJECT_OVERVIEW.md` at end of session with what changed

---

## 🔧 Development Commands

```bash
# Start dev stack (API + worker + Postgres + Redis)
make dev

# Stop dev stack
make dev-stop

# Follow logs
make dev-logs

# Run tests (no Docker needed)
cd backend && python -m pytest tests/ -v

# Run linting
cd backend && ruff check . && ruff format --check .

# Apply DB migrations
make migrate

# Connect to dev DB
make shell-db
```

### Required Environment Variables

Copy `.env.saas.template` → `.env.saas` and fill in values:

| Variable | Required | Purpose |
|----------|----------|---------|
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://app:app@db:5432/komoot_strava_sync` |
| `REDIS_URL` | ✅ | `redis://redis:6379` |
| `SECRET_KEY` | ✅ | JWT signing key (32+ random bytes) |
| `KOMOOT_ENCRYPTION_KEY` | ✅ | Fernet key for credential encryption |
| `STRAVA_CLIENT_ID` | ✅ | From Strava developer app |
| `STRAVA_CLIENT_SECRET` | ✅ | From Strava developer app |
| `STRAVA_WEBHOOK_VERIFY_TOKEN` | Optional | Strava webhook challenge verification |
| `STRIPE_SECRET_KEY` | Optional | Stripe billing |
| `STRIPE_WEBHOOK_SECRET` | Optional | Stripe webhook signature verification |
| `STRIPE_PRICE_PRO` | Optional | Stripe price ID for Pro tier |

---

## 🚦 Where to Continue Next

**Priority order:**

### 1. Frontend (Next.js dashboard) — Highest impact
- Login/register page
- Dashboard: sync status, activity history, connection status
- Settings: connect Komoot + Strava, configure sync interval
- Billing: subscription status, upgrade flow
- Rules editor (Pro tier)

### 2. Komoot Exponential Backoff
- Add retry with backoff in `KomootClient` for 429/5xx responses
- Critical before launch to avoid IP blocks at scale

### 3. Multi-App Strava Routing
- Implement `StravaApp` selection logic in `poll_komoot_user` job
- Load-balance across multiple registered Strava apps
- Required for >200 active cloud users

### 4. Self-Hosted License Validation
- Wire `LicenseCache` table to `require_tier()` dependency
- License key validates feature set without cloud dependency

### 5. Admin Endpoints
- Strava app pool management (add/remove/view quota)
- User management for self-hosted deployments
- Job audit log viewer

### 6. Notification Delivery
- Email on sync failure, activity synced milestone
- `NotificationSettings` model already exists

---

## 📋 Critical Code Rules (Never Violate)

1. **Python 3.9+ only** — use `from __future__ import annotations` at top of every file, `Optional[X]` not `X | None`
2. **Async everywhere** — no blocking I/O in route handlers or services, use `httpx.AsyncClient`, SQLAlchemy async session only
3. **ALL Strava calls through `RateLimitGuard`** — `await rate_limit_guard.call(app_id, tier, fn, ...)` — never call Strava directly
4. **Credentials always encrypted** — Komoot email/password and Strava tokens always stored as Fernet-encrypted bytes, never plaintext
5. **Multi-tenant scoping** — every DB query for user data must include `WHERE user_id = :user_id`
6. **Komoot API is unofficial** — handle all Komoot HTTP errors gracefully, never crash the worker, log and continue
7. **No bare `except: pass`** — explicit error handling with logging

### Key Patterns

```python
# DB query pattern
result = await db.execute(select(User).where(User.id == user_id))
user = result.scalar_one_or_none()

# Rate-limited Strava call
result = await rate_limit_guard.call(app_id, tier, strava_client.upload_gpx, ...)

# Encrypt/decrypt credentials
from app.core.security import encrypt, decrypt
user.komoot_password_encrypted = encrypt(raw_password)
password = decrypt(user.komoot_password_encrypted)

# Tier-gated endpoint
@router.post("/rules")
async def create_rule(
    user: User = Depends(get_current_user),
    _tier: None = Depends(require_tier("pro")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]: ...
```

---

## 📝 Session Log

| Date | AI Tool | What Changed |
|------|---------|-------------|
| 2026-04-17 | Claude Code | Added CODEX.md, rewrote Alembic migration 001, fixed Strava token encryption in OAuth callback, added token refresh in worker paths, fixed webhook user resolution (athlete_id), reverse-sync through RateLimitGuard, added test coverage |
| 2026-04-18 | Claude Code | Verified 20 tests passing, validated migration on clean Postgres 16, added env templates, updated docker-compose (backend-only), added new API endpoints (sync/status, activities detail, rules CRUD, api-keys delete, disconnect endpoints, register/login/refresh, GPX download), expanded test coverage to 20 tests |
| 2026-04-18 | Claude Code | Reorganized project structure (app/ → legacy/), created PROJECT_OVERVIEW.md, removed merged worktree branches |
