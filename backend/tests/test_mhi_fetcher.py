import httpx
import pytest

from app.interface_adapters.gateways.mhi_fetcher import MhiPressReleaseFetcher
from app.use_cases.article_fetcher import ArticleFetcher
from app.use_cases.errors import ArticleSourceUnavailableError, SourceStructureChangedError

NEWS_RSS = """<?xml version="1.0"?><rss version="2.0"><channel>
<item>
  <title>潜水艦の進水式を実施<br/>副題</title>
  <link>https://www.mhi.com/jp/news/261008.html</link>
  <pubDate>Thu, 08 Oct 2026 11:00:00 +0900</pubDate>
</item>
<item>
  <title>巡視船の引渡式を実施</title>
  <link>https://www.mhi.com/jp/news/261001.html</link>
  <pubDate>Thu, 01 Oct 2026 11:00:00 +0900</pubDate>
</item>
</channel></rss>"""

ARTICLE_HTML = '<div class="field--name-field-detail1"><p>本文テキスト</p></div>'


def build_client(article_response: httpx.Response) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(".xml"):
            return httpx.Response(200, text=NEWS_RSS)
        return article_response

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_recent_articles_builds_articles_from_rss_and_article_pages() -> None:
    fetcher: ArticleFetcher = MhiPressReleaseFetcher(
        build_client(httpx.Response(200, text=ARTICLE_HTML))
    )

    articles = fetcher.fetch_recent_articles(limit=5)

    assert [article.url for article in articles] == [
        "https://www.mhi.com/jp/news/261008.html",
        "https://www.mhi.com/jp/news/261001.html",
    ]
    assert articles[0].source == "mhi"
    assert articles[0].title == "潜水艦の進水式を実施 副題"
    assert articles[0].body == "本文テキスト"


def test_fetch_recent_articles_respects_limit() -> None:
    fetcher = MhiPressReleaseFetcher(build_client(httpx.Response(200, text=ARTICLE_HTML)))

    assert len(fetcher.fetch_recent_articles(limit=1)) == 1


@pytest.mark.parametrize(
    ("article_response", "expected_error"),
    [
        (httpx.Response(500), ArticleSourceUnavailableError),
        (httpx.Response(200, text="<p>本文フィールドなし</p>"), SourceStructureChangedError),
    ],
    ids=["http_error", "body_field_missing"],
)
def test_fetch_recent_articles_raises_when_all_bodies_unavailable(
    article_response: httpx.Response, expected_error: type[Exception]
) -> None:
    fetcher = MhiPressReleaseFetcher(build_client(article_response))

    with pytest.raises(expected_error, match="試した2件の記事本文をすべて"):
        fetcher.fetch_recent_articles(limit=5)


def test_fetch_recent_articles_raises_when_rss_request_fails() -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(503)))

    with pytest.raises(ArticleSourceUnavailableError, match="ニュースRSSの取得に失敗"):
        MhiPressReleaseFetcher(client).fetch_recent_articles()


def test_fetch_recent_articles_propagates_structure_change() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text="<html></html>"))
    )

    with pytest.raises(SourceStructureChangedError):
        MhiPressReleaseFetcher(client).fetch_recent_articles()
