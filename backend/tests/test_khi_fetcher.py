import httpx
import pytest

from app.interface_adapters.gateways.khi_fetcher import KhiPressReleaseFetcher
from app.use_cases.article_fetcher import ArticleFetcher
from app.use_cases.errors import ArticleSourceUnavailableError, SourceStructureChangedError
from tests.conftest import build_minimal_pdf

NEWS_RSS = """<?xml version="1.0"?><rss version="2.0"><channel>
<item>
  <title>共同開発を完了</title>
  <link>https://www.khi.co.jp/pressrelease/news_261014-1.pdf</link>
  <pubDate>Wed,14 Oct 2026 11:00:00 +0900</pubDate>
</item>
<item>
  <title>運転試験に成功</title>
  <link>https://www.khi.co.jp/pressrelease/detail/20261008_1.html</link>
  <pubDate>Thu, 8 Oct 2026 11:00:00 +0900</pubDate>
</item>
</channel></rss>"""

ARTICLE_HTML = '<div class="news-detail-area"><p>HTML本文</p></div>'


def build_client(
    pdf_response: httpx.Response | None = None, html_response: httpx.Response | None = None
) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(".xml"):
            return httpx.Response(200, text=NEWS_RSS)
        if request.url.path.endswith(".pdf"):
            return pdf_response or httpx.Response(200, content=build_minimal_pdf("PDF Body"))
        return html_response or httpx.Response(200, text=ARTICLE_HTML)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_recent_articles_reads_both_pdf_and_html_articles() -> None:
    fetcher: ArticleFetcher = KhiPressReleaseFetcher(build_client())

    articles = fetcher.fetch_recent_articles(limit=5)

    assert [(article.title, article.body) for article in articles] == [
        ("共同開発を完了", "PDF Body"),
        ("運転試験に成功", "HTML本文"),
    ]
    assert articles[0].source == "khi"
    assert articles[0].url == "https://www.khi.co.jp/pressrelease/news_261014-1.pdf"


def test_fetch_recent_articles_respects_limit() -> None:
    fetcher = KhiPressReleaseFetcher(build_client())

    assert len(fetcher.fetch_recent_articles(limit=1)) == 1


@pytest.mark.parametrize(
    "pdf_response",
    [
        httpx.Response(404),
        httpx.Response(200, content=b"not a pdf"),
        httpx.Response(200, content=build_minimal_pdf("")),
    ],
    ids=["http_error", "broken_pdf", "empty_text"],
)
def test_fetch_recent_articles_skips_pdf_article_when_text_unavailable(
    pdf_response: httpx.Response,
) -> None:
    fetcher = KhiPressReleaseFetcher(build_client(pdf_response=pdf_response))

    assert [article.body for article in fetcher.fetch_recent_articles()] == ["HTML本文"]


@pytest.mark.parametrize(
    "html_response",
    [httpx.Response(500), httpx.Response(200, text="<p>本文の領域なし</p>")],
    ids=["http_error", "detail_area_missing"],
)
def test_fetch_recent_articles_skips_html_article_when_body_unavailable(
    html_response: httpx.Response,
) -> None:
    fetcher = KhiPressReleaseFetcher(build_client(html_response=html_response))

    assert [article.body for article in fetcher.fetch_recent_articles()] == ["PDF Body"]


@pytest.mark.parametrize(
    ("pdf_response", "html_response", "expected_error"),
    [
        (httpx.Response(503), httpx.Response(503), ArticleSourceUnavailableError),
        (httpx.Response(404), httpx.Response(503), SourceStructureChangedError),
    ],
    ids=["all_transient", "not_found_included"],
)
def test_fetch_recent_articles_raises_when_all_bodies_unavailable(
    pdf_response: httpx.Response, html_response: httpx.Response, expected_error: type[Exception]
) -> None:
    fetcher = KhiPressReleaseFetcher(build_client(pdf_response, html_response))

    with pytest.raises(expected_error, match="試した2件の記事本文をすべて"):
        fetcher.fetch_recent_articles()


def test_fetch_recent_articles_raises_when_rss_request_fails() -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(503)))

    with pytest.raises(ArticleSourceUnavailableError, match="ニュースRSSの取得に失敗"):
        KhiPressReleaseFetcher(client).fetch_recent_articles()


def test_fetch_recent_articles_propagates_structure_change() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text="<html></html>"))
    )

    with pytest.raises(SourceStructureChangedError):
        KhiPressReleaseFetcher(client).fetch_recent_articles()
