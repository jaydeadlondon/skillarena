import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_route():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_version_route():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/version")
    assert response.status_code == 200
    assert response.json()["app"] == "SkillArena"
    assert response.json()["version"] == "0.9.0"


@pytest.mark.asyncio
async def test_home_route():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert "SkillArena" in response.text


@pytest.mark.asyncio
async def test_unknown_route_404():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/definitely-not-existing")
    assert response.status_code == 404
    assert "Quest not found" in response.text


@pytest.mark.asyncio
async def test_post_without_csrf_is_forbidden():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post("/ai/dashboard/plan")
    assert response.status_code == 403
