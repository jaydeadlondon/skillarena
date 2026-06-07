import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_trusted_host_allows_testserver():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/health", headers={"host": "testserver"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_trusted_host_rejects_unknown_host():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/health", headers={"host": "evil.example"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_same_origin_post_passes_csrf_then_hits_auth_redirect():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        response = await client.post(
            "/ai/dashboard/plan",
            headers={"origin": "http://testserver", "host": "testserver"},
        )
    assert response.status_code == 307
    assert response.json()["detail"] == "Temporary Redirect"


@pytest.mark.asyncio
async def test_cross_origin_post_without_token_is_forbidden():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/ai/dashboard/plan",
            headers={"origin": "http://evil.example", "host": "testserver"},
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_activity_heartbeat_is_csrf_exempt_but_still_requires_auth():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        response = await client.post(
            "/activity/heartbeat",
            json={"activity_type": "general", "seconds": 5},
            headers={"origin": "http://evil.example", "host": "testserver"},
        )
    assert response.status_code == 307
    assert response.json()["detail"] == "Temporary Redirect"
