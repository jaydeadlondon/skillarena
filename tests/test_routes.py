from fastapi.testclient import TestClient

from app.main import app


def test_health_route():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_home_route():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "SkillArena" in response.text


def test_unknown_route_404():
    client = TestClient(app)
    response = client.get("/definitely-not-existing")
    assert response.status_code == 404
    assert "Quest not found" in response.text


def test_post_without_csrf_is_forbidden():
    client = TestClient(app)
    response = client.post("/ai/dashboard/plan")
    assert response.status_code == 403
