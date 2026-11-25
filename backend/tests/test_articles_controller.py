from collections.abc import Iterator
from datetime import UTC, date, datetime
from unittest.mock import MagicMock, create_autospec

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.interface_adapters.controllers.articles_controller import build_articles_router
from app.use_cases.article_summary_reader import SummarizedArticle
from app.use_cases.list_summarized_articles import JST, SummarizedArticleLister

SUMMARIZED_ARTICLE = SummarizedArticle(
    article_id=1,
    source="mod",
    url="https://www.mod.go.jp/j/press/news/2026/11/18a.html",
    title="お知らせ",
    published_at=datetime(2026, 11, 18, tzinfo=JST),
    summary_text="概要: お知らせ。",
    matched_categories=(),
    mentions_price=False,
    mentions_israel=False,
    summarized_at=datetime(2026, 11, 17, 21, tzinfo=UTC),
)


def make_client(lister: MagicMock) -> TestClient:
    def provide_lister() -> Iterator[SummarizedArticleLister]:
        yield lister

    app = FastAPI()
    app.include_router(build_articles_router(provide_lister))
    return TestClient(app)


def make_lister() -> MagicMock:
    lister: MagicMock = create_autospec(SummarizedArticleLister, instance=True)
    lister.list_for.return_value = (SUMMARIZED_ARTICLE,)
    lister.today.return_value = date(2026, 11, 25)
    return lister


def test_returns_articles_for_requested_date() -> None:
    lister = make_lister()

    response = make_client(lister).get("/articles", params={"date": "2026-11-18"})

    assert response.status_code == 200
    body = response.json()
    assert body["date"] == "2026-11-18"
    assert [article["article_id"] for article in body["articles"]] == [1]
    lister.list_for.assert_called_once_with(date(2026, 11, 18))


def test_uses_today_in_jst_when_date_is_omitted() -> None:
    lister = make_lister()
    lister.list_for.return_value = ()

    response = make_client(lister).get("/articles")

    assert response.status_code == 200
    assert response.json() == {"date": "2026-11-25", "articles": []}
    lister.list_for.assert_called_once_with(date(2026, 11, 25))


def test_rejects_invalid_date_format_with_422() -> None:
    lister = make_lister()

    response = make_client(lister).get("/articles", params={"date": "2026/11/18"})

    assert response.status_code == 422
    lister.list_for.assert_not_called()
