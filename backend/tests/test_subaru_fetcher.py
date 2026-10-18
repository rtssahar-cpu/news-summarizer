import httpx
import pytest

from app.interface_adapters.gateways.subaru_fetcher import SubaruNewsReleaseFetcher
from app.use_cases.article_fetcher import ArticleFetcher
from app.use_cases.errors import ArticleSourceUnavailableError, SourceStructureChangedError

NEWS_LIST_HTML = """
<div class="component-newsList"><div><ul>
  <li><time>2026/10/05</time><p><a href="/news/2026_10_05_171759">展示会に出展</a></p></li>
  <li><time>2026/10/02</time><p><a href="/news/2026_10_02_160447">大会に協賛</a></p></li>
</ul></div></div>
"""

FIRST_ARTICLE_PATH = "/news/2026_10_05_171759"


def build_client(first_article_response: httpx.Response | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/news/":
            return httpx.Response(200, text=NEWS_LIST_HTML)
        if request.url.path == FIRST_ARTICLE_PATH and first_article_response is not None:
            return first_article_response
        return httpx.Response(200, text=f'<div id="text"><p>{request.url.path}の本文</p></div>')

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_recent_articles_returns_articles_with_body() -> None:
    fetcher: ArticleFetcher = SubaruNewsReleaseFetcher(build_client())

    articles = fetcher.fetch_recent_articles(limit=5)

    assert [(article.title, article.body) for article in articles] == [
        ("展示会に出展", f"{FIRST_ARTICLE_PATH}の本文"),
        ("大会に協賛", "/news/2026_10_02_160447の本文"),
    ]
    assert articles[0].source == "subaru"
    assert articles[0].url == f"https://www.subaru.co.jp{FIRST_ARTICLE_PATH}"


def test_fetch_recent_articles_respects_limit() -> None:
    fetcher = SubaruNewsReleaseFetcher(build_client())

    assert len(fetcher.fetch_recent_articles(limit=1)) == 1


@pytest.mark.parametrize(
    "first_article_response",
    [httpx.Response(500), httpx.Response(200, text="<p>本文の領域なし</p>")],
    ids=["http_error", "text_area_missing"],
)
def test_fetch_recent_articles_skips_article_when_body_unavailable(
    first_article_response: httpx.Response,
) -> None:
    fetcher = SubaruNewsReleaseFetcher(build_client(first_article_response))

    assert [article.title for article in fetcher.fetch_recent_articles()] == ["大会に協賛"]


def test_fetch_recent_articles_raises_when_news_list_request_fails() -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(503)))

    with pytest.raises(ArticleSourceUnavailableError, match="ニュース一覧ページの取得に失敗"):
        SubaruNewsReleaseFetcher(client).fetch_recent_articles()


def test_fetch_recent_articles_propagates_structure_change() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text="<html></html>"))
    )

    with pytest.raises(SourceStructureChangedError):
        SubaruNewsReleaseFetcher(client).fetch_recent_articles()
