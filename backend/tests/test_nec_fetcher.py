import httpx
import pytest

from app.interface_adapters.gateways.nec_fetcher import NecPressReleaseFetcher
from app.use_cases.article_fetcher import ArticleFetcher
from app.use_cases.errors import ArticleSourceUnavailableError, SourceStructureChangedError

NEWS_RSS = """<?xml version="1.0"?><rss version="2.0"><channel>
<item>
  <link>https://jpn.nec.com/press/202610/20261014_01.html</link>
  <title>VLM技術を開発</title>
  <pubDate>Wed, 14 Oct 2026 10:00:00 +0900</pubDate>
</item>
<item>
  <link>https://jpn.nec.com/press/202610/20261013_01.html</link>
  <title>VRアプリケーションを共同開発</title>
  <pubDate>Tue, 13 Oct 2026 10:00:00 +0900</pubDate>
</item>
</channel></rss>"""

FIRST_ARTICLE_PATH = "/press/202610/20261014_01.html"


def build_article_html(body: str) -> str:
    return f'<div class="str-column-main"><p>{body}</p></div>'


def build_client(first_article_response: httpx.Response | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(".xml"):
            return httpx.Response(200, text=NEWS_RSS)
        if request.url.path == FIRST_ARTICLE_PATH and first_article_response is not None:
            return first_article_response
        return httpx.Response(200, text=build_article_html(f"本文 {request.url.path}"))

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_recent_articles_reads_article_pages() -> None:
    fetcher: ArticleFetcher = NecPressReleaseFetcher(build_client())

    articles = fetcher.fetch_recent_articles(limit=5)

    assert [(article.title, article.body) for article in articles] == [
        ("VLM技術を開発", f"本文 {FIRST_ARTICLE_PATH}"),
        ("VRアプリケーションを共同開発", "本文 /press/202610/20261013_01.html"),
    ]
    assert articles[0].source == "nec"
    assert articles[0].url == f"https://jpn.nec.com{FIRST_ARTICLE_PATH}"


def test_fetch_recent_articles_respects_limit() -> None:
    fetcher = NecPressReleaseFetcher(build_client())

    assert len(fetcher.fetch_recent_articles(limit=1)) == 1


@pytest.mark.parametrize(
    "first_article_response",
    [httpx.Response(500), httpx.Response(200, text="<p>本文の領域なし</p>")],
    ids=["http_error", "main_column_missing"],
)
def test_fetch_recent_articles_skips_article_when_body_unavailable(
    first_article_response: httpx.Response,
) -> None:
    fetcher = NecPressReleaseFetcher(build_client(first_article_response))

    assert [article.title for article in fetcher.fetch_recent_articles()] == [
        "VRアプリケーションを共同開発"
    ]


def test_fetch_recent_articles_raises_when_rss_request_fails() -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(503)))

    with pytest.raises(ArticleSourceUnavailableError, match="ニュースRSSの取得に失敗"):
        NecPressReleaseFetcher(client).fetch_recent_articles()


def test_fetch_recent_articles_propagates_structure_change() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text="<html></html>"))
    )

    with pytest.raises(SourceStructureChangedError):
        NecPressReleaseFetcher(client).fetch_recent_articles()
