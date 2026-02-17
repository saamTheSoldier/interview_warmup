"""
Health endpoint tests - TDD: fast feedback on API availability.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    """GET /api/v1/health returns 200 and status ok."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_ready(client: AsyncClient):
    """GET /api/v1/health/ready returns 200."""
    response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
