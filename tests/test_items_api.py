"""
Item API tests - REST CRUD and validation (TDD).
Challenge: Ensure endpoints return correct status codes and shape.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_items_empty(client: AsyncClient):
    """GET /api/v1/items returns 200 and list (possibly empty)."""
    response = await client.get("/api/v1/items")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_item_requires_auth(client: AsyncClient):
    """POST /api/v1/items without token returns 403 (or 401)."""
    response = await client.post(
        "/api/v1/items",
        json={"title": "Foo", "description": "Bar", "price_cents": 100, "owner_id": 1},
    )
    # Endpoint uses CurrentUserId dependency -> 403 if no credentials
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_item_with_auth(client: AsyncClient, auth_headers: dict, test_user):
    """POST /api/v1/items with valid token creates item and returns 201."""
    response = await client.post(
        "/api/v1/items",
        headers=auth_headers,
        json={
            "title": "Test Item",
            "description": "Desc",
            "price_cents": 999,
            "owner_id": test_user.id,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Item"
    assert data["price_cents"] == 999
    assert "id" in data
