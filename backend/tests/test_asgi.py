from collections.abc import Iterator
from datetime import date
from unittest.mock import MagicMock, create_autospec, patch

from fastapi.testclient import TestClient

from app.frameworks import asgi
from app.frameworks.asgi import create_app
from app.use_cases.errors import ArticleStorageError
from app.use_cases.list_summarized_articles import SummarizedArticleLister


def make_client(lister: MagicMock) -> TestClient:
    def provide_lister() -> Iterator[SummarizedArticleLister]:
        yield lister

    return TestClient(create_app(app_version="test-sha", provide_lister=provide_lister))


def test_articles_endpoint_uses_injected_lister() -> None:
    lister = create_autospec(SummarizedArticleLister, instance=True)
    lister.list_for.return_value = ()

    response = make_client(lister).get("/articles", params={"date": "2026-11-18"})

    assert response.status_code == 200
    assert response.json() == {"date": "2026-11-18", "articles": []}
    lister.list_for.assert_called_once_with(date(2026, 11, 18))


def test_storage_error_is_converted_to_500_by_registered_handler() -> None:
    lister = create_autospec(SummarizedArticleLister, instance=True)
    lister.list_for.side_effect = ArticleStorageError("DBに接続できません")

    response = make_client(lister).get("/articles", params={"date": "2026-11-18"})

    assert response.status_code == 500
    assert response.json() == {"detail": "サーバー内部でエラーが発生しました"}


def test_provider_closes_session_after_response() -> None:
    session = MagicMock()
    with patch.object(asgi, "SessionLocal", return_value=session):
        provider = asgi.provide_summarized_article_lister()
        lister = next(provider)
        session.__exit__.assert_not_called()
        provider.close()

    assert isinstance(lister, SummarizedArticleLister)
    session.__exit__.assert_called_once()
