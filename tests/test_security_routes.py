from fastapi.testclient import TestClient

from app.main import app


def test_trusted_host_allows_testserver():
    client = TestClient(app)
    response = client.get("/health", headers={"host": "testserver"})
    assert response.status_code == 200


def test_trusted_host_rejects_unknown_host():
    client = TestClient(app)
    response = client.get("/health", headers={"host": "evil.example"})
    assert response.status_code == 400


def test_same_origin_post_passes_csrf_then_hits_auth_redirect():
    client = TestClient(app, follow_redirects=False)
    response = client.post(
        "/ai/dashboard/plan",
        headers={"origin": "http://testserver", "host": "testserver"},
    )
    assert response.status_code == 307
    assert response.json()["detail"] == "Temporary Redirect"


def test_cross_origin_post_without_token_is_forbidden():
    client = TestClient(app)
    response = client.post(
        "/ai/dashboard/plan",
        headers={"origin": "http://evil.example", "host": "testserver"},
    )
    assert response.status_code == 403


def test_activity_heartbeat_is_csrf_exempt_but_still_requires_auth():
    client = TestClient(app, follow_redirects=False)
    response = client.post(
        "/activity/heartbeat",
        json={"activity_type": "general", "seconds": 5},
        headers={"origin": "http://evil.example", "host": "testserver"},
    )
    assert response.status_code == 307
    assert response.json()["detail"] == "Temporary Redirect"
