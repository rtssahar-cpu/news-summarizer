from fastapi.testclient import TestClient

from app.frameworks.asgi import create_app


def test_health_check_returns_ok_with_injected_version() -> None:
    client = TestClient(create_app(app_version="test-sha"))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "test-sha"}
