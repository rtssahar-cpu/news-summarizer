from collections.abc import Callable

import httpx
import pytest

from app.interface_adapters.gateways.mod_fetcher import ModPressReleaseFetcher
from app.use_cases.errors import ArticleSourceUnavailableError, SourceStructureChangedError
from tests.conftest import build_minimal_pdf


def build_rss(*notice_ids: str) -> str:
    items = "".join(
        f"<item><title>お知らせ{notice_id}</title>"
        f"<link>/j/press/news/2026/10/{notice_id}.html</link></item>"
        for notice_id in notice_ids
    )
    return f'<?xml version="1.0"?><rss version="2.0"><channel>{items}</channel></rss>'


def build_client(
    rss_xml: str, pdf_handler: Callable[[httpx.Request], httpx.Response]
) -> tuple[httpx.Client, list[str]]:
    requested_pdf_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(".pdf"):
            requested_pdf_paths.append(request.url.path)
            return pdf_handler(request)
        return httpx.Response(200, text=rss_xml)

    return httpx.Client(transport=httpx.MockTransport(handler)), requested_pdf_paths


def respond_pdf(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, content=build_minimal_pdf("Article Body Text"))


def respond_not_found(request: httpx.Request) -> httpx.Response:
    return httpx.Response(404)


def test_fetch_recent_articles_builds_article_from_rss_and_pdf() -> None:
    client, requested_pdf_paths = build_client(build_rss("16c"), respond_pdf)

    articles = ModPressReleaseFetcher(client).fetch_recent_articles(limit=5)

    assert requested_pdf_paths == ["/j/press/news/2026/10/16c.pdf"]
    assert len(articles) == 1
    assert articles[0].source == "mod"
    assert articles[0].url == "https://www.mod.go.jp/j/press/news/2026/10/16c.html"
    assert articles[0].title == "お知らせ16c"
    assert articles[0].body == "Article Body Text"


def test_fetch_recent_articles_tries_next_notice_until_limit_when_pdf_missing() -> None:
    def respond_pdf_except_16b(request: httpx.Request) -> httpx.Response:
        return respond_not_found(request) if "16b" in request.url.path else respond_pdf(request)

    client, requested_pdf_paths = build_client(
        build_rss("16c", "16b", "16a", "15a"), respond_pdf_except_16b
    )

    articles = ModPressReleaseFetcher(client).fetch_recent_articles(limit=2)

    assert [article.title for article in articles] == ["お知らせ16c", "お知らせ16a"]
    assert len(requested_pdf_paths) == 3


def test_fetch_recent_articles_stops_after_max_attempts() -> None:
    notice_ids = [f"{day:02d}a" for day in range(1, 11)]
    client, requested_pdf_paths = build_client(build_rss(*notice_ids), respond_not_found)

    with pytest.raises(SourceStructureChangedError, match="試した6件の記事本文をすべて"):
        ModPressReleaseFetcher(client).fetch_recent_articles(limit=2)

    assert len(requested_pdf_paths) == 6


def test_fetch_recent_articles_raises_source_unavailable_when_all_pdfs_fail_transiently() -> None:
    client, _ = build_client(build_rss("16c", "16b"), lambda request: httpx.Response(503))

    with pytest.raises(ArticleSourceUnavailableError, match="試した2件の記事本文をすべて"):
        ModPressReleaseFetcher(client).fetch_recent_articles(limit=5)


def test_fetch_recent_articles_skips_item_when_pdf_is_broken() -> None:
    def respond_broken_pdf_for_16c(request: httpx.Request) -> httpx.Response:
        if "16c" in request.url.path:
            return httpx.Response(200, content=b"not a pdf")
        return respond_pdf(request)

    client, _ = build_client(build_rss("16c", "16b"), respond_broken_pdf_for_16c)

    articles = ModPressReleaseFetcher(client).fetch_recent_articles(limit=5)

    assert [article.title for article in articles] == ["お知らせ16b"]


def _raise_connect_error(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("connection refused", request=request)


@pytest.mark.parametrize(
    "rss_handler",
    [lambda request: httpx.Response(503), _raise_connect_error],
    ids=["http_503", "connect_error"],
)
def test_fetch_recent_articles_raises_source_unavailable_when_rss_fails(
    rss_handler: Callable[[httpx.Request], httpx.Response],
) -> None:
    client = httpx.Client(transport=httpx.MockTransport(rss_handler))

    with pytest.raises(ArticleSourceUnavailableError) as exc_info:
        ModPressReleaseFetcher(client).fetch_recent_articles(limit=5)

    assert exc_info.value.source == "mod"
    assert isinstance(exc_info.value.__cause__, httpx.HTTPError)


def test_fetch_recent_articles_raises_structure_changed_when_no_notice_found() -> None:
    client, _ = build_client(build_rss(), respond_pdf)

    with pytest.raises(SourceStructureChangedError):
        ModPressReleaseFetcher(client).fetch_recent_articles(limit=5)
