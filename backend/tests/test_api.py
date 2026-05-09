import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_ok(client: AsyncClient):
    r = await client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("ok", "degraded")
    assert "environment" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_listings_returns_200(client: AsyncClient):
    r = await client.get("/listings")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data


@pytest.mark.asyncio
async def test_listings_pagination_params(client: AsyncClient):
    r = await client.get("/listings?page=1&per_page=5")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_listings_invalid_page(client: AsyncClient):
    r = await client.get("/listings?page=0")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_deployments_returns_200(client: AsyncClient):
    r = await client.get("/deployments")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_record_deployment(client: AsyncClient):
    payload = {
        "environment":  "staging",
        "version":      "abc1234",
        "image_tag":    "church-finder-backend:abc1234",
        "deployed_by":  "test-ci",
        "notes":        "Test deploy",
    }
    r = await client.post("/deployments", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["environment"] == "staging"
    assert data["version"]     == "abc1234"
    assert data["is_current"]  is True


@pytest.mark.asyncio
async def test_rollback_missing_id(client: AsyncClient):
    r = await client.post("/deployments/rollback", json={
        "target_deployment_id": "00000000-0000-0000-0000-000000000000",
        "reason": "test",
    })
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_crawl_runs_returns_200(client: AsyncClient):
    r = await client.get("/listings/runs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    