import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.interface_adapters.controllers.error_handlers import (
    EXTERNAL_SERVICE_ERROR_DETAIL,
    INTERNAL_ERROR_DETAIL,
    register_error_handlers,
)
from app.use_cases.errors import (
    ArticleSourceUnavailableError,
    ArticleStorageError,
)


def make_client_raising(error: Exception) -> TestClient:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/failing")
    def failing_endpoint() -> None:
        raise error

    # 想定外の例外はStarletteが応答の後に投げ直すため、テストクライアントには伝えない設定にする
    return TestClient(app, raise_server_exceptions=False)


def test_unexpected_error_returns_500_with_same_json_shape() -> None:
    client = make_client_raising(TypeError("unexpected"))

    response = client.get("/failing")

    assert response.status_code == 500
    assert response.json() == {"detail": INTERNAL_ERROR_DETAIL}


def test_internal_error_returns_500_without_leaking_reason(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = make_client_raising(ArticleStorageError("connection refused"))

    with caplog.at_level(logging.WARNING):
        response = client.get("/failing")

    assert response.status_code == 500
    assert response.json() == {"detail": INTERNAL_ERROR_DETAIL}
    assert [record.levelno for record in caplog.records] == [logging.ERROR]
    assert "connection refused" in caplog.text


def test_external_service_error_returns_503_and_logs_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = make_client_raising(ArticleSourceUnavailableError("mod", "timeout"))

    with caplog.at_level(logging.WARNING):
        response = client.get("/failing")

    assert response.status_code == 503
    assert response.json() == {"detail": EXTERNAL_SERVICE_ERROR_DETAIL}
    assert [record.levelno for record in caplog.records] == [logging.WARNING]
    assert "timeout" not in response.text
