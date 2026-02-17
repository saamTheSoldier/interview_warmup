"""
BDD step definitions for health feature (pytest-bdd).
Challenge: Express requirements in Gherkin; map to HTTP calls.
"""

import pytest
from pytest_bdd import scenarios, when, then
from httpx import AsyncClient, ASGITransport

from app.main import app

# Load all scenarios from the feature file
scenarios("../features/health.feature")


@pytest.fixture
def response():
    """Store last response for then steps."""
    return {}


@pytest.mark.asyncio
@when('I request "GET" "/api/v1/health"')
async def request_health(response):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/v1/health")
        response["status"] = r.status_code
        response["body"] = r.json()


@pytest.mark.asyncio
@when('I request "GET" "/api/v1/health/ready"')
async def request_ready(response):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/v1/health/ready")
        response["status"] = r.status_code
        response["body"] = r.json()


@then('the response status should be 200')
def status_200(response):
    assert response["status"] == 200


@then('the response body should have "status" equals "ok"')
def body_status_ok(response):
    assert response["body"].get("status") == "ok"


@then('the response body should have "status" equals "ready"')
def body_status_ready(response):
    assert response["body"].get("status") == "ready"
