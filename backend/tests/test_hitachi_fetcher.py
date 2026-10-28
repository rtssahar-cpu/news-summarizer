import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.interface_adapters.gateways.hitachi_fetcher import HitachiNewsFetcher
from app.use_cases.article_fetcher import ArticleFetcher
from app.use_cases.errors import ArticleSourceUnavailableError, SourceStructureChangedError
from tests.conftest import build_minimal_pdf

JST = timezone(timedelta(hours=9))
NEWS_LIST_JSON_PATH = (
    "/content/hitachi/global/ja_jp/press/jcr:content/root/main-container/"
    "initial-container/page_search_copy_cop.json"
)
FIRST_ARTICLE_URL = "https://www.hitachi.com/ja-jp/press/articles/2026/10/1016a/"
FIRST_PDF_PATH = "/content/dam/hitachi/global/ja_jp/press/files/2026/10/1016a.pdf"
SECOND_ARTICLE_URL = "https://www.hitachi.com/ja-jp/press/articles/2026/10/1009a/"

NEWS_LIST_JSON = json.dumps(
    {
        "searchPagesList": [
            {
                "newsPath": FIRST_ARTICLE_URL,
                "newsTitle": "覚書を締結",
                "publishDateValue": "2026-10-16T17:00:00",
            },
            {
                "newsPath": SECOND_ARTICLE_URL,
                "newsTitle": "プログラムに参画",
                "publishDateValue": "2026-10-09T09:00:00",
            },
        ]
    },
    ensure_ascii=False,
)


def build_client(first_pdf_response: httpx.Response | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == NEWS_LIST_JSON_PATH:
            return httpx.Response(200, text=NEWS_LIST_JSON)
        if request.url.path == FIRST_PDF_PATH and first_pdf_response is not None:
            return first_pdf_response
        # build_minimal_pdf はlatin-1のテキストしか扱えないため、ファイル名を本文にする
        file_name = request.url.path.rsplit("/", 1)[-1]
        return httpx.Response(200, content=build_minimal_pdf(f"{file_name} body"))

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_recent_articles_returns_articles_with_pdf_body() -> None:
    fetcher: ArticleFetcher = HitachiNewsFetcher(build_client())

    articles = fetcher.fetch_recent_articles(limit=5)

    assert [(article.title, article.body) for article in articles] == [
        ("覚書を締結", "1016a.pdf body"),
        ("プログラムに参画", "1009a.pdf body"),
    ]
    assert articles[0].source == "hitachi"
    # URLにはPDFではなく、人が読む記事ページのURLを保存する
    assert articles[0].url == FIRST_ARTICLE_URL
    assert articles[0].published_at == datetime(2026, 10, 16, 17, 0, tzinfo=JST)


def test_fetch_recent_articles_respects_limit() -> None:
    fetcher = HitachiNewsFetcher(build_client())

    assert len(fetcher.fetch_recent_articles(limit=1)) == 1


@pytest.mark.parametrize(
    "first_pdf_response",
    [
        httpx.Response(404),
        httpx.Response(200, content=b"not a pdf"),
        httpx.Response(200, content=build_minimal_pdf("")),
    ],
    ids=["http_error", "broken_pdf", "empty_text"],
)
def test_fetch_recent_articles_skips_article_when_body_unavailable(
    first_pdf_response: httpx.Response,
) -> None:
    fetcher = HitachiNewsFetcher(build_client(first_pdf_response))

    assert [article.title for article in fetcher.fetch_recent_articles()] == ["プログラムに参画"]


@pytest.mark.parametrize(
    ("article_response", "expected_error"),
    [
        (httpx.Response(503), ArticleSourceUnavailableError),
        (httpx.Response(404), SourceStructureChangedError),
    ],
    ids=["http_503", "http_404"],
)
def test_fetch_recent_articles_raises_when_all_bodies_unavailable(
    article_response: httpx.Response, expected_error: type[Exception]
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == NEWS_LIST_JSON_PATH:
            return httpx.Response(200, text=NEWS_LIST_JSON)
        return article_response

    fetcher = HitachiNewsFetcher(httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(expected_error, match="試した2件の記事本文をすべて"):
        fetcher.fetch_recent_articles()


def test_fetch_recent_articles_raises_when_news_list_request_fails() -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(503)))

    with pytest.raises(ArticleSourceUnavailableError, match="ニュース一覧のJSONの取得に失敗"):
        HitachiNewsFetcher(client).fetch_recent_articles()


def test_fetch_recent_articles_propagates_structure_change() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text="<html></html>"))
    )

    with pytest.raises(SourceStructureChangedError):
        HitachiNewsFetcher(client).fetch_recent_articles()
