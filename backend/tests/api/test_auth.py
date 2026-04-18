from __future__ import annotations
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.db.models.user import StravaToken, User


@pytest.mark.asyncio
async def test_get_strava_login_url(async_client: AsyncClient):
    """Test generating the Strava login OAuth URI."""
    # We must skip authentication override for this since we want to see it just works
    response = await async_client.get("/api/v1/auth/strava/login")
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert "https://www.strava.com/oauth/authorize" in data["url"]
    assert "response_type=code" in data["url"]
    # Verify the configured frontend URL is passed as the redirect
    assert "strava-callback" in data["url"]


@pytest.mark.asyncio
async def test_setup_komoot_connection(async_client: AsyncClient):
    """Test that Komoot credentials are encrypted correctly."""
    # We mock out the dependency in `app.api.deps`
    from app.api import deps
    from app.main import app
    
    # Fake user object mimicking the sqlalchemy model
    fake_user = User(id="00000000-0000-0000-0000-000000000000", email="test@test.com")
    
    # Mocking get_current_user logic so we don't need real DB or JWT token auth
    app.dependency_overrides[deps.get_current_user] = lambda: fake_user
    
    # We still mock DB commit for testing endpoints that just save state
    class FakeDB:
        async def commit(self):
            pass
            
    app.dependency_overrides[deps.get_db] = lambda: FakeDB()

    response = await async_client.post(
        "/api/v1/auth/komoot",
        json={
            "email": "my_komoot@email.com",
            "password": "super_secret_komoot_pw",
            "user_id": "123456789"
        }
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # Verify the fake user got its properties updated 
    assert fake_user.komoot_user_id == "123456789"
    assert fake_user.komoot_email_encrypted is not None
    assert fake_user.komoot_password_encrypted is not None
    assert fake_user.sync_komoot_to_strava is True
    
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_strava_callback_stores_encrypted_tokens(async_client: AsyncClient):
    """OAuth callback must encrypt Strava tokens before storing them."""
    from app.api import deps
    from app.main import app

    fake_user = User(id="00000000-0000-0000-0000-000000000000", email="test@test.com")
    added_objects = []

    app.dependency_overrides[deps.get_current_user] = lambda: fake_user

    class FakeDB:
        def add(self, obj):
            added_objects.append(obj)

        async def commit(self):
            pass

    app.dependency_overrides[deps.get_db] = lambda: FakeDB()

    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {
        "access_token": "plain_access_token",
        "refresh_token": "plain_refresh_token",
        "expires_at": int(datetime(2026, 4, 18, tzinfo=timezone.utc).timestamp()),
        "athlete": {"id": 123456},
    }

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.return_value = fake_response

    with patch("app.api.v1.auth.httpx.AsyncClient", return_value=mock_client):
        response = await async_client.post(
            "/api/v1/auth/strava/callback",
            json={"code": "test_code"},
        )

    assert response.status_code == 200
    assert len(added_objects) == 1

    token = added_objects[0]
    assert isinstance(token, StravaToken)
    assert token.access_token != b"plain_access_token"
    assert token.refresh_token != b"plain_refresh_token"
    assert token.strava_athlete_id == 123456

    app.dependency_overrides.clear()
