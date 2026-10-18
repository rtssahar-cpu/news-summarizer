import httpx
import pytest

from app.interface_adapters.gateways.ihi_fetcher import IhiNewsFetcher
from app.use_cases.article_fetcher import ArticleFetcher
from app.use_cases.errors import ArticleSourceUnavailableError, SourceStructureChangedError

FIRST_ARTICLE_PATH = "/all_news/2026/industrial_general_machine/1202210_13803.html"
SECOND_ARTICLE_PATH = "/all_news/2026/aeroengine_space_defense/1202146_13805.html"


def build_item(date_text: str, path: str, title: str) -> str:
    return f"""
<li><div class="m-news_text">
  <div class="m-news_items"><time>{date_text}</time></div>
  <p><a href="{path}">{title}</a></p>
</div></li>
"""


NEWS_LIST_HTML = f"""
<div id="tab01"><ul class="m-news">
  {build_item("2026年10月07日", FIRST_ARTICLE_PATH, "圧縮機が採用")}
  {build_item("2026年07月22日", SECOND_ARTICLE_PATH, "SAR衛星のトレーニングを開始")}
</ul></div>
"""


def build_client(first_article_response: httpx.Response | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/all_news/":
            return httpx.Response(200, text=NEWS_LIST_HTML)
        if request.url.path == FIRST_ARTICLE_PATH and first_article_response is not None:
            return first_article_response
        return httpx.Response(
            200, text=f'<div class="m-entry-detail"><p>{request.url.path}の本文</p></div>'
        )

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_recent_articles_returns_articles_with_body() -> None:
    fetcher: ArticleFetcher = IhiNewsFetcher(build_client())

    articles = fetcher.fetch_recent_articles(limit=5)

    assert [(article.title, article.body) for article in articles] == [
        ("圧縮機が採用", f"{FIRST_ARTICLE_PATH}の本文"),
        ("SAR衛星のトレーニングを開始", f"{SECOND_ARTICLE_PATH}の本文"),
    ]
    assert articles[0].source == "ihi"
    assert articles[0].url == f"https://www.ihi.co.jp{FIRST_ARTICLE_PATH}"


def test_fetch_recent_articles_respects_limit() -> None:
    fetcher = IhiNewsFetcher(build_client())

    assert len(fetcher.fetch_recent_articles(limit=1)) == 1


@pytest.mark.parametrize(
    "first_article_response",
    [httpx.Response(500), httpx.Response(200, text="<p>本文の領域なし</p>")],
    ids=["http_error", "detail_area_missing"],
)
def test_fetch_recent_articles_skips_article_when_body_unavailable(
    first_article_response: httpx.Response,
) -> None:
    fetcher = IhiNewsFetcher(build_client(first_article_response))

    assert [article.title for article in fetcher.fetch_recent_articles()] == [
        "SAR衛星のトレーニングを開始"
    ]


def test_fetch_recent_articles_raises_when_news_list_request_fails() -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(503)))

    with pytest.raises(ArticleSourceUnavailableError, match="ニュース一覧ページの取得に失敗"):
        IhiNewsFetcher(client).fetch_recent_articles()


def test_fetch_recent_articles_propagates_structure_change() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text="<html></html>"))
    )

    with pytest.raises(SourceStructureChangedError):
        IhiNewsFetcher(client).fetch_recent_articles()
