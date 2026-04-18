from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.db.models.user import User


@pytest.mark.asyncio
async def test_register_login_and_refresh(async_client: AsyncClient):
    """Test account registration, login, and token refresh."""
    from app.api import deps
    from app.main import app
    from app.db.models.subscription import Subscription

    db_state: dict[str, object | None] = {
        "user": None,
        "subscription": None,
    }

    class FakeResult:
        def __init__(self, scalar_val=None):
            self._scalar = scalar_val

        def scalar_one_or_none(self):
            return self._scalar

    class FakeDB:
        async def execute(self, stmt):
            stmt_str = str(stmt).lower()
            if "where users.email" in stmt_str:
                return FakeResult(scalar_val=db_state["user"])
            return FakeResult()

        def add(self, obj):
            if isinstance(obj, User):
                obj.id = "00000000-0000-0000-0000-000000000000"
                db_state["user"] = obj
            elif isinstance(obj, Subscription):
                db_state["subscription"] = obj

        async def commit(self):
            pass

    app.dependency_overrides[deps.get_db] = lambda: FakeDB()

    with patch("app.api.v1.auth.security.hash_password", return_value="hashed_pw"), patch(
        "app.api.v1.auth.security.verify_password", return_value=True
    ):
        register_response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "test@test.com", "password": "secret123"},
        )
        assert register_response.status_code == 200
        assert "access_token" in register_response.json()
        assert db_state["user"] is not None
        assert db_state["subscription"] is not None

        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "test@test.com", "password": "secret123"},
        )
        assert login_response.status_code == 200
        assert "access_token" in login_response.json()

        app.dependency_overrides[deps.get_current_user] = lambda: db_state["user"]
        refresh_response = await async_client.post("/api/v1/auth/refresh")
        assert refresh_response.status_code == 200
        assert "access_token" in refresh_response.json()

    app.dependency_overrides.clear()
