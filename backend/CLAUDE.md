# Backend Architecture Reference

Compact guide for subagents implementing the SaaS backend. Read this instead of exploring the codebase.

## Stack

| Layer | Technology |
|---|---|
| API | FastAPI (async) |
| DB ORM | SQLAlchemy 2.0 async (`AsyncSession`) |
| DB | PostgreSQL (via `asyncpg`) |
| Migrations | Alembic |
| Queue / cache | Redis + ARQ (async job queue) |
| Encryption | `cryptography.fernet.Fernet` |
| Auth | JWT (`python-jose`) + Bearer tokens |
| Payments | Stripe |
| HTTP clients | `httpx` (async) |
| Config | `pydantic-settings` BaseSettings |

## Directory Map

```
backend/
├── app/
│   ├── main.py                  # FastAPI app factory, lifespan, router include
│   ├── api/
│   │   ├── deps.py              # get_db, get_current_user, require_tier, get_current_api_key_user
│   │   └── v1/
│   │       ├── router.py        # includes all sub-routers → /api/v1/...
│   │       ├── auth.py          # /auth/strava/*, /auth/komoot/*
│   │       ├── sync.py          # /sync/status, /sync/trigger
│   │       ├── activities.py    # /activities, /activities/{id}/gpx
│   │       ├── routes.py        # /routes/* (planned tours, Pro+)
│   │       ├── rules.py         # /rules/* (filter rules, Pro+)
│   │       ├── billing.py       # /billing/checkout, /billing/portal
│   │       ├── webhooks.py      # /webhooks/strava (Strava push), /webhooks/stripe
│   │       └── api_keys.py      # /api-keys/* (Pro+)
│   ├── core/
│   │   ├── config.py            # Settings class — all env vars live here
│   │   ├── security.py          # JWT create/verify, Fernet encrypt/decrypt, API key gen
│   │   └── rate_limit.py        # RateLimitGuard — wraps ALL outbound Strava API calls
│   ├── db/
│   │   ├── session.py           # async_engine, AsyncSessionLocal, get_db()
│   │   └── models/
│   │       ├── user.py          # User, StravApp, StravaToken
│   │       ├── subscription.py  # Subscription, ApiKey, WebhookSubscription, NotificationSettings
│   │       └── sync.py          # SyncedActivity, UserSyncState, SyncRule, JobAuditLog, LicenseCache
│   ├── services/
│   │   ├── komoot.py            # KomootClient (async httpx, per-user credentials)
│   │   ├── strava.py            # StravaClient (async httpx, per-user tokens, rate-limited)
│   │   └── sync.py              # SyncService — orchestrates Komoot↔Strava
│   └── jobs/
│       ├── worker.py            # ARQ WorkerSettings, cron schedule
│       └── sync_jobs.py         # poll_komoot_user, process_strava_activity, komoot_poll_scheduler
├── alembic/
│   ├── env.py
│   └── versions/001_initial_schema.py
├── tests/
│   └── conftest.py              # client, db, free/pro/business_user_headers fixtures
├── requirements.txt
├── pyproject.toml               # includes [tool.pytest.ini_options] asyncio_mode = "auto"
└── Dockerfile
```

## Core Patterns

### Config (app/core/config.py)
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379"
    SECRET_KEY: str                      # JWT signing
    KOMOOT_ENCRYPTION_KEY: str           # Fernet key for Komoot credentials
    STRAVA_CLIENT_ID: str                # shared Strava app
    STRAVA_CLIENT_SECRET: str
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    LICENSE_SERVER_URL: str = ""         # for self-hosted license validation
    ENVIRONMENT: str = "production"      # "development" | "production"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
```

### DB Session (app/db/session.py)
```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

### Auth Dependencies (app/api/deps.py)
```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validates JWT, returns User. Raises 401 if invalid/expired."""

async def require_tier(min_tier: str):
    """Returns a FastAPI dependency that raises 402 if user tier is insufficient."""
    # Tier ranks: free=0, pro=1, business=2

async def get_current_api_key_user(
    api_key: str = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validates hashed API key, returns User. Raises 401 if invalid."""
```

### Route Template
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db, require_tier
from app.db.models.user import User

router = APIRouter(prefix="/sync", tags=["sync"])

@router.post("/trigger", response_model=SyncTriggerResponse)
async def trigger_sync(
    user: User = Depends(get_current_user),
    _tier: None = Depends(require_tier("pro")),   # omit for free-tier endpoints
    db: AsyncSession = Depends(get_db),
):
    """Trigger a manual sync. (full docstring added by document-and-test skill)"""
```

### DB Query Patterns
```python
from sqlalchemy import select, update, delete

# Select one
result = await db.execute(select(User).where(User.id == user_id))
user = result.scalar_one_or_none()

# Insert
db.add(SyncRule(user_id=user.id, **data))
await db.commit()
await db.refresh(new_rule)

# Update with RETURNING
stmt = update(User).where(User.id == uid).values(**kw).returning(User)
updated = (await db.execute(stmt)).scalar_one()
await db.commit()

# Delete
await db.execute(delete(SyncRule).where(SyncRule.id == rid, SyncRule.user_id == uid))
await db.commit()
```

### Encryption (Komoot credentials)
```python
from cryptography.fernet import Fernet
from app.core.config import settings

def get_fernet() -> Fernet:
    return Fernet(settings.KOMOOT_ENCRYPTION_KEY.encode())

encrypted = get_fernet().encrypt(plaintext.encode())
plaintext = get_fernet().decrypt(encrypted).decode()
```

### Rate Limit Guard (app/core/rate_limit.py)
```python
class RateLimitGuard:
    """Wraps ALL outbound Strava API calls. Tracks per-app 15-min + daily budgets in Redis."""
    
    async def call(self, app_id: int, tier: str, fn: Callable, *args, **kwargs):
        # 1. INCR Redis f"strava:{app_id}:rl:15min:{window}" TTL=900
        # 2. INCR Redis f"strava:{app_id}:rl:daily:{date}" TTL=86400
        # 3. If 15min > 90 or daily > 950: re-queue with delay, raise RateLimitError
        # 4. Execute fn(*args, **kwargs)
        # Priority: business=15, pro=10, free=5
```

### ARQ Jobs
```python
# In sync_jobs.py
async def poll_komoot_user(ctx: dict, user_id: str) -> None:
    """Fetches new Komoot tours and uploads them to Strava for one user."""

async def process_strava_activity(ctx: dict, user_id: str, activity_id: str) -> None:
    """Handles Strava webhook event — syncs activity to Komoot (beta)."""

async def komoot_poll_scheduler(ctx: dict) -> None:
    """Cron: queries users with next_komoot_poll_at <= now(), enqueues poll jobs."""
```

## SQLAlchemy Model Conventions
- All PKs: `id: Mapped[UUID] = mapped_column(default=uuid4)`
- Timestamps: `created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))`
- All models inherit from `Base = DeclarativeBase()`
- Encrypted columns: `BYTEA` type, encrypted before write, decrypted after read
- Enums as plain strings with `CheckConstraint` (no Python Enum, simpler migrations)

## Tier Ranks
```
free = 0  (default for all new users)
pro  = 1
business = 2
```
Tier stored as string in `subscriptions.tier`. Rank computed at runtime.

## Error HTTP Codes
| Situation | Code |
|---|---|
| Missing/invalid JWT | 401 |
| Insufficient tier | 402 |
| Forbidden resource | 403 |
| Not found | 404 |
| External API failure | 502 |

## Key External API Notes
- **Strava rate limit**: 100 req/15min, 1000 req/day **per app** (shared across all users). ALL Strava calls MUST go through `RateLimitGuard`.
- **Komoot API**: unofficial `https://www.komoot.de/api/v007`, Basic Auth, no webhooks.
- **Strava webhook**: one subscription per app → receives events for all authorized athletes. `owner_id` in each event maps to `strava_tokens.strava_athlete_id`.
- **Komoot credentials**: encrypted with Fernet before storing. Key NEVER goes in DB.
