from __future__ import annotations

"""
Pytest configuration and fixtures.

Env vars are bootstrapped before any app import so pydantic-settings can
construct the Settings object without a .env file.
"""

import os
from collections.abc import AsyncGenerator

# ── env vars must come before any app import ──────────────────────────────────
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("SECRET_KEY", "testsecretkey0000000000000000000")
os.environ.setdefault("STRAVA_CLIENT_ID", "12345")
os.environ.setdefault("STRAVA_CLIENT_SECRET", "test_strava_secret")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

from cryptography.fernet import Fernet  # noqa: E402

os.environ["KOMOOT_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
# ──────────────────────────────────────────────────────────────────────────────

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api import deps  # noqa: E402
from app.core import security  # noqa: E402
from app.db import models as _models  # noqa: E402, F401 — ensure all models registered
from app.db.base import Base  # noqa: E402
from app.db.models.subscription import Subscription  # noqa: E402
from app.db.models.user import User  # noqa: E402
from app.main import app  # noqa: E402

# ── Database fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """In-memory SQLite session with the full schema — isolated per test function."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def async_client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """ASGI test client wired to the real in-memory SQLite DB session."""
    app.dependency_overrides[deps.get_db] = lambda: db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()


# ── User fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
async def free_user(db: AsyncSession) -> User:
    """A persisted free-tier user."""
    user = User(
        email="free@test.com",
        password_hash=security.hash_password("password"),
        is_active=True,
    )
    db.add(user)
    db.add(Subscription(user=user, tier="free", status="active"))
    await db.commit()
    return user


@pytest.fixture
async def pro_user(db: AsyncSession) -> User:
    """A persisted pro-tier user."""
    user = User(
        email="pro@test.com",
        password_hash=security.hash_password("password"),
        is_active=True,
    )
    db.add(user)
    db.add(Subscription(user=user, tier="pro", status="active"))
    await db.commit()
    return user


@pytest.fixture
def free_user_headers(free_user: User) -> dict[str, str]:
    """Bearer token headers for the free user."""
    return {"Authorization": f"Bearer {security.create_access_token(str(free_user.id))}"}


@pytest.fixture
def pro_user_headers(pro_user: User) -> dict[str, str]:
    """Bearer token headers for the pro user."""
    return {"Authorization": f"Bearer {security.create_access_token(str(pro_user.id))}"}
