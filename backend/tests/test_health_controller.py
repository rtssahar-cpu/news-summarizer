from collections.abc import Iterator

from fastapi.testclient import TestClient

from app.frameworks.asgi import create_app
from app.use_cases.list_summarized_articles import SummarizedArticleLister


def unused_lister_provider() -> Iterator[SummarizedArticleLister]:
    raise AssertionError("/health はユースケースを使わない")
    yield  # ジェネレーター関数にするための到達しない yield


def test_health_check_returns_ok_with_injected_version() -> None:
    client = TestClient(create_app(app_version="test-sha", provide_lister=unused_lister_provider))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "test-sha"}
