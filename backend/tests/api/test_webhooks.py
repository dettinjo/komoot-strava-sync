from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_stripe_webhook_rejects_invalid_signature(async_client: AsyncClient):
    """The Stripe webhook endpoint must reject payloads with bad signatures."""
    from app.core.config import settings

    settings.STRIPE_SECRET_KEY = "sk_test_fake"
    settings.STRIPE_WEBHOOK_SECRET = "whsec_fake"

    response = await async_client.post(
        "/api/v1/webhooks/stripe",
        content=b"{}",
        headers={"Stripe-Signature": "t=123,v1=bad_signature"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid signature"


@pytest.mark.asyncio
async def test_verify_strava_webhook(async_client: AsyncClient):
    """GET challenge verification must echo back the hub.challenge."""
    from unittest.mock import patch

    token = "super_secret_token_abc123"

    # Patch the settings object the endpoint reads from
    with patch("app.api.v1.webhooks.settings") as mock_settings:
        mock_settings.STRAVA_WEBHOOK_VERIFY_TOKEN = token

        # FastAPI maps hub_verify_token param from query string "hub_verify_token" (underscores)
        response = await async_client.get(
            "/api/v1/webhooks/strava"
            f"?hub_mode=subscribe&hub_challenge=15f7bn&hub_verify_token={token}"
        )

    assert response.status_code == 200
    assert response.json() == {"hub.challenge": "15f7bn"}


@pytest.mark.asyncio
async def test_receive_strava_webhook(async_client: AsyncClient):
    """POST from Strava should be accepted and the job enqueued."""
    from app.api import deps
    from app.main import app

    # Provide a mock ARQ pool on the app state
    mock_arq = AsyncMock()
    mock_arq.enqueue_job = AsyncMock()
    app.state.arq_pool = mock_arq

    class FakeDB:
        async def execute(self, stmt):
            class _R:
                def scalar_one_or_none(self):
                    return None

            return _R()

    app.dependency_overrides[deps.get_db] = lambda: FakeDB()

    payload = {
        "aspect_type": "create",
        "event_time": 1549560669,
        "object_id": 1234567890,
        "object_type": "activity",
        "owner_id": 99999,
        "subscription_id": 120475,
    }

    response = await async_client.post("/api/v1/webhooks/strava", json=payload)

    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    mock_arq.enqueue_job.assert_called_once()

    app.dependency_overrides.clear()
    del app.state.arq_pool
