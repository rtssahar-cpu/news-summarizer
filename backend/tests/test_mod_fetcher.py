from collections.abc import Callable

import httpx
import pytest

from app.interface_adapters.gateways.mod_fetcher import ModPressReleaseFetcher
from app.use_cases.errors import ArticleSourceUnavailableError, SourceStructureChangedError
from tests.conftest import build_minimal_pdf

NOTICE_HTML = """
<div class="news__item">
    <dt class="date">9/19</dt>
    <dd class="news__title">
        <a href="/j/approach/anpo/2026/0918a_usa-j.html">日米電話会談について</a>
        <a href="/j/approach/anpo/2026/pdf/0918a_usa-j.pdf" target="_blank">印刷用</a>
    </dd>
</div>
"""

NOTICE_HTML_WITHOUT_PDF = """
<div class="news__item">
    <dt class="date">9/18</dt>
    <dd class="news__title">
        <a href="/j/press/news/2026/09/18a.html">PDFなしのお知らせ</a>
    </dd>
</div>
"""


def test_fetch_recent_articles_builds_article_from_notice_and_pdf() -> None:
    pdf_bytes = build_minimal_pdf("Article Body Text")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(".pdf"):
            return httpx.Response(200, content=pdf_bytes)
        return httpx.Response(200, text=NOTICE_HTML)

    client = httpx.Client(transport=httpx.MockTransport(handler))

    articles = ModPressReleaseFetcher(client).fetch_recent_articles(limit=5)

    assert len(articles) == 1
    assert articles[0].source == "mod"
    assert articles[0].title == "日米電話会談について"
    assert articles[0].body == "Article Body Text"


def test_fetch_recent_articles_skips_item_when_pdf_fetch_fails() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(".pdf"):
            return httpx.Response(500)
        return httpx.Response(200, text=NOTICE_HTML)

    client = httpx.Client(transport=httpx.MockTransport(handler))

    articles = ModPressReleaseFetcher(client).fetch_recent_articles(limit=5)

    assert articles == []


def test_fetch_recent_articles_skips_item_without_pdf_link() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text=NOTICE_HTML_WITHOUT_PDF)
        )
    )

    articles = ModPressReleaseFetcher(client).fetch_recent_articles(limit=5)

    assert articles == []


def test_fetch_recent_articles_skips_item_when_pdf_is_broken() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(".pdf"):
            return httpx.Response(200, content=b"not a pdf")
        return httpx.Response(200, text=NOTICE_HTML)

    client = httpx.Client(transport=httpx.MockTransport(handler))

    articles = ModPressReleaseFetcher(client).fetch_recent_articles(limit=5)

    assert articles == []


def _raise_connect_error(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("connection refused", request=request)


@pytest.mark.parametrize(
    "notice_list_handler",
    [lambda request: httpx.Response(503), _raise_connect_error],
    ids=["http_503", "connect_error"],
)
def test_fetch_recent_articles_raises_source_unavailable_when_notice_list_fails(
    notice_list_handler: Callable[[httpx.Request], httpx.Response],
) -> None:
    client = httpx.Client(transport=httpx.MockTransport(notice_list_handler))

    with pytest.raises(ArticleSourceUnavailableError) as exc_info:
        ModPressReleaseFetcher(client).fetch_recent_articles(limit=5)

    assert exc_info.value.source == "mod"
    assert isinstance(exc_info.value.__cause__, httpx.HTTPError)


def test_fetch_recent_articles_raises_structure_changed_when_no_notice_found() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text="<html></html>"))
    )

    with pytest.raises(SourceStructureChangedError):
        ModPressReleaseFetcher(client).fetch_recent_articles(limit=5)
