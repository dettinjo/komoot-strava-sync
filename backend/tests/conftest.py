from __future__ import annotations
"""Pytest configuration and fixtures.

We must bootstrap the required env-vars before importing the app so that
pydantic-settings can construct the Settings object.  Tests run in complete
isolation — every variable is a dummy value; no real infrastructure is hit.
"""

import os

# ── Set required env vars before any app import ─────────────────────────────
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("SECRET_KEY", "testsecretkey0000000000000000000")
# A valid 32-byte base64url Fernet key for unit tests
os.environ.setdefault(
    "KOMOOT_ENCRYPTION_KEY",
    "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAw"  # 32 bytes of '0', base64-encoded
    "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAw"
    # correct 32-byte Fernet-compatible key:
)
# Use a proper Fernet key (44 chars, URL-safe base64)
os.environ["KOMOOT_ENCRYPTION_KEY"] = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAw" + "AAAA"
# Generate a real one to be safe
from cryptography.fernet import Fernet
os.environ["KOMOOT_ENCRYPTION_KEY"] = Fernet.generate_key().decode()

os.environ.setdefault("STRAVA_CLIENT_ID", "12345")
os.environ.setdefault("STRAVA_CLIENT_SECRET", "test_strava_secret")
# ────────────────────────────────────────────────────────────────────────────

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
async def async_client() -> AsyncClient:
    """Async test client for FastAPI routes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
