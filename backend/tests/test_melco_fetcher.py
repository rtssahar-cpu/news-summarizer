import json
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.interface_adapters.gateways.melco_fetcher import MelcoNewsFetcher
from app.use_cases.article_fetcher import ArticleFetcher
from app.use_cases.errors import ArticleSourceUnavailableError, SourceStructureChangedError
from tests.conftest import build_minimal_pdf

JST = timezone(timedelta(hours=9))
BASE_URL = "https://www.mitsubishielectric.co.jp"
NEWS_LIST_JSON_PATH = "/global/common/mel25/news-data/jws-news/japan/www/ja/news-article.json"
FIRST_ARTICLE_PATH = "/ja/pr/2026/0820_ei/"
FIRST_PDF_PATH = "/ja/pr/2026/pdf/0820_ei.pdf"
PDF_ONLY_PATH = "/ja/pr/2026/pdf/0807_pu.pdf"
SPLIT_ARTICLE_HTML = (
    '<ul><li><a href="/ja/pr/2026/pdf/0820_ei1.pdf">お知らせ</a></li>'
    '<li><a href="/ja/pr/2026/pdf/0820_ei2.pdf">説明会資料</a></li></ul>'
)

NEWS_LIST_JSON = json.dumps(
    {
        "news": [
            {
                "title": "完全子会社化",
                "url": FIRST_ARTICLE_PATH,
                "articlePublishtime": "2026-08-20T15:00:00+09:00",
            },
            {
                "title": "PDFのみの発表",
                "url": PDF_ONLY_PATH,
                "articlePublishtime": "2026-08-07T11:00:00+09:00",
            },
        ]
    },
    ensure_ascii=False,
)


def build_client(overrides: Mapping[str, httpx.Response] | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == NEWS_LIST_JSON_PATH:
            return httpx.Response(200, text=NEWS_LIST_JSON)
        if overrides is not None and request.url.path in overrides:
            return overrides[request.url.path]
        # build_minimal_pdf はlatin-1のテキストしか扱えないため、ファイル名を本文にする
        file_name = request.url.path.rsplit("/", 1)[-1]
        return httpx.Response(200, content=build_minimal_pdf(f"{file_name} body"))

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_recent_articles_returns_articles_with_pdf_body() -> None:
    fetcher: ArticleFetcher = MelcoNewsFetcher(build_client())

    articles = fetcher.fetch_recent_articles(limit=5)

    assert [(article.title, article.body) for article in articles] == [
        ("完全子会社化", "0820_ei.pdf body"),
        ("PDFのみの発表", "0807_pu.pdf body"),
    ]
    assert articles[0].source == "melco"
    # URLにはPDFではなく、人が読む記事ページのURLを保存する
    assert articles[0].url == f"{BASE_URL}{FIRST_ARTICLE_PATH}"
    assert articles[0].published_at == datetime(2026, 8, 20, 15, 0, tzinfo=JST)


def test_fetch_recent_articles_respects_limit() -> None:
    fetcher = MelcoNewsFetcher(build_client())

    assert len(fetcher.fetch_recent_articles(limit=1)) == 1


def test_fetch_recent_articles_joins_split_pdfs_when_full_text_pdf_not_found() -> None:
    client = build_client(
        {
            FIRST_PDF_PATH: httpx.Response(404),
            FIRST_ARTICLE_PATH: httpx.Response(200, text=SPLIT_ARTICLE_HTML),
        }
    )

    article = MelcoNewsFetcher(client).fetch_recent_articles(limit=1)[0]

    assert article.body == "0820_ei1.pdf body\n0820_ei2.pdf body"


@pytest.mark.parametrize(
    "overrides",
    [
        {FIRST_PDF_PATH: httpx.Response(500)},
        {FIRST_PDF_PATH: httpx.Response(200, content=b"not a pdf")},
        {FIRST_PDF_PATH: httpx.Response(200, content=build_minimal_pdf(""))},
        {FIRST_PDF_PATH: httpx.Response(404), FIRST_ARTICLE_PATH: httpx.Response(404)},
        {
            FIRST_PDF_PATH: httpx.Response(404),
            FIRST_ARTICLE_PATH: httpx.Response(200, text="<html></html>"),
        },
        {
            FIRST_PDF_PATH: httpx.Response(404),
            FIRST_ARTICLE_PATH: httpx.Response(200, text=SPLIT_ARTICLE_HTML),
            "/ja/pr/2026/pdf/0820_ei2.pdf": httpx.Response(404),
        },
    ],
    ids=[
        "server_error",
        "broken_pdf",
        "empty_text",
        "article_page_not_found",
        "no_split_pdf",
        "split_pdf_not_found",
    ],
)
def test_fetch_recent_articles_skips_article_when_body_unavailable(
    overrides: Mapping[str, httpx.Response],
) -> None:
    fetcher = MelcoNewsFetcher(build_client(overrides))

    assert [article.title for article in fetcher.fetch_recent_articles()] == ["PDFのみの発表"]


def test_fetch_recent_articles_does_not_look_for_split_pdfs_of_pdf_only_news() -> None:
    requested_paths: list[str] = []
    inner_client = build_client({PDF_ONLY_PATH: httpx.Response(404)})

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        return inner_client.get(str(request.url))

    fetcher = MelcoNewsFetcher(httpx.Client(transport=httpx.MockTransport(handler)))

    assert [article.title for article in fetcher.fetch_recent_articles()] == ["完全子会社化"]
    assert requested_paths == [NEWS_LIST_JSON_PATH, FIRST_PDF_PATH, PDF_ONLY_PATH]


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

    fetcher = MelcoNewsFetcher(httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(expected_error, match="試した2件の記事本文をすべて"):
        fetcher.fetch_recent_articles()


def test_fetch_recent_articles_raises_when_news_list_request_fails() -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(503)))

    with pytest.raises(ArticleSourceUnavailableError, match="ニュース一覧のJSONの取得に失敗"):
        MelcoNewsFetcher(client).fetch_recent_articles()


def test_fetch_recent_articles_propagates_structure_change() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text="<html></html>"))
    )

    with pytest.raises(SourceStructureChangedError):
        MelcoNewsFetcher(client).fetch_recent_articles()
