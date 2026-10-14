import httpx

from app.interface_adapters.gateways.mod_fetcher import ModPressReleaseFetcher
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
