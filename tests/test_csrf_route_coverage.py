import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

CSRF_PROTECTED_POST_ROUTES = [
    "/focus/complete",
    "/notifications/read-all",
    "/quests/1/claim",
    "/pvp/create",
    "/shop/1/buy",
    "/learn/lessons/1/progress",
    "/admin/courses",
    "/admin/ai-generate-quests",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("path", CSRF_PROTECTED_POST_ROUTES)
async def test_csrf_protected_routes_reject_cross_origin_posts(path: str):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            path,
            headers={"origin": "http://evil.example", "host": "testserver"},
        )
    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid or missing CSRF token."


@pytest.mark.asyncio
@pytest.mark.parametrize("path", CSRF_PROTECTED_POST_ROUTES)
async def test_csrf_protected_routes_allow_same_origin_then_require_auth(path: str):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        response = await client.post(
            path,
            headers={"origin": "http://testserver", "host": "testserver"},
        )
    assert response.status_code == 307
    assert response.json()["detail"] == "Temporary Redirect"


@pytest.mark.asyncio
async def test_logout_rejects_cross_origin_without_csrf():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/auth/logout",
            headers={"origin": "http://evil.example", "host": "testserver"},
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_logout_allows_same_origin():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        response = await client.post(
            "/auth/logout",
            headers={"origin": "http://testserver", "host": "testserver"},
        )
    assert response.status_code == 303
    assert response.headers["location"] == "/"
