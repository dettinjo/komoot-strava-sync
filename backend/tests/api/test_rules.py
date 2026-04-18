import pytest
from httpx import AsyncClient

from app.db.models.sync import SyncRule
from app.db.models.user import User


@pytest.mark.asyncio
async def test_create_and_list_rules(async_client: AsyncClient):
    """Test generating a new SyncRule and listing them."""
    from app.api import deps
    from app.db.models.subscription import Subscription
    from app.main import app

    fake_user = User(id="00000000-0000-0000-0000-000000000000", is_active=True)
    fake_sub = Subscription(user_id=fake_user.id, tier="pro", status="active")

    app.dependency_overrides[deps.get_current_user] = lambda: fake_user

    mock_db_state: list = []

    class FakeResult:
        def __init__(self, scalar_val=None, items=None):
            self._scalar = scalar_val
            self._items = items if items is not None else []

        def scalar_one_or_none(self):
            return self._scalar

        def scalars(self):
            items = self._items

            class _S:
                def all(self):
                    return items

            return _S()

    class FakeDB:
        async def execute(self, stmt):
            stmt_str = str(stmt).lower()
            if "subscriptions" in stmt_str:
                return FakeResult(scalar_val=fake_sub)
            if "sync_rules" in stmt_str:
                return FakeResult(items=mock_db_state)
            return FakeResult()

        def add(self, obj):
            mock_db_state.append(obj)

        async def commit(self):
            pass

    app.dependency_overrides[deps.get_db] = lambda: FakeDB()

    # Create rule
    payload = {
        "name": "Ignore Ebikes",
        "direction": "komoot_to_strava",
        "conditions": {"sport": "ebike"},
        "actions": {"sync_to": "None"},
        "rule_order": 1,
    }

    response = await async_client.post("/api/v1/rules", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # List rules
    # Manually populate an ID to avoid stringification failures
    mock_db_state[0].id = "11111111-1111-1111-1111-111111111111"
    response_list = await async_client.get("/api/v1/rules")
    assert response_list.status_code == 200
    list_data = response_list.json()
    assert len(list_data["data"]) == 1
    assert list_data["data"][0]["name"] == "Ignore Ebikes"
    assert list_data["data"][0]["direction"] == "komoot_to_strava"
    assert list_data["data"][0]["conditions"] == {"sport": "ebike"}

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_and_delete_rule(async_client: AsyncClient):
    """Test updating and deleting an existing rule."""
    from app.api import deps
    from app.db.models.subscription import Subscription
    from app.main import app

    fake_user = User(id="00000000-0000-0000-0000-000000000000", is_active=True)
    fake_sub = Subscription(user_id=fake_user.id, tier="pro", status="active")
    existing_rule = SyncRule(
        id="11111111-1111-1111-1111-111111111111",
        user_id=fake_user.id,
        name="Old Rule",
        direction="komoot_to_strava",
        conditions={"sport": "ride"},
        actions={"sync_to": "Strava"},
        rule_order=0,
        is_active=True,
    )

    app.dependency_overrides[deps.get_current_user] = lambda: fake_user

    class FakeResult:
        def __init__(self, scalar_val=None):
            self._scalar = scalar_val

        def scalar_one_or_none(self):
            return self._scalar

    class FakeDB:
        async def execute(self, stmt):
            stmt_str = str(stmt).lower()
            if "subscriptions" in stmt_str:
                return FakeResult(scalar_val=fake_sub)
            return FakeResult(scalar_val=existing_rule)

        async def commit(self):
            pass

        async def delete(self, obj):
            obj.deleted = True

    app.dependency_overrides[deps.get_db] = lambda: FakeDB()

    update_response = await async_client.put(
        f"/api/v1/rules/{existing_rule.id}",
        json={
            "name": "Updated Rule",
            "direction": "both",
            "conditions": {"sport": "run"},
            "actions": {"sync_to": "None"},
            "rule_order": 2,
            "is_active": False,
        },
    )
    assert update_response.status_code == 200
    assert existing_rule.name == "Updated Rule"
    assert existing_rule.direction == "both"
    assert existing_rule.is_active is False

    delete_response = await async_client.delete(f"/api/v1/rules/{existing_rule.id}")
    assert delete_response.status_code == 200
    assert getattr(existing_rule, "deleted", False) is True

    app.dependency_overrides.clear()
