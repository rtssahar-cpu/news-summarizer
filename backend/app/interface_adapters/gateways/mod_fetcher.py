import logging

import httpx

from app.entities.article import Article
from app.interface_adapters.gateways.article_body_failures import (
    ArticleBodyFailure,
    build_all_bodies_failed_error,
)
from app.interface_adapters.gateways.http_headers import USER_AGENT
from app.interface_adapters.gateways.mod_rss_parser import SOURCE_NAME, parse_mod_news_rss
from app.interface_adapters.gateways.pdf_text import extract_pdf_text
from app.use_cases.errors import ArticleContentUnavailableError, ArticleSourceUnavailableError

NEWS_RSS_URL = "https://www.mod.go.jp/j/rss/news.xml"
# PDF版がないお知らせも多いため、limit件そろうまで先の記事も試す（負荷を抑えるため上限あり）
MAX_ATTEMPTS_PER_ARTICLE = 3

logger = logging.getLogger(__name__)


class ModPressReleaseFetcher:
    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def fetch_recent_articles(self, limit: int = 5) -> list[Article]:
        notices = parse_mod_news_rss(self._fetch_news_rss())
        articles: list[Article] = []
        body_failures: list[ArticleBodyFailure] = []

        for notice in notices[: limit * MAX_ATTEMPTS_PER_ARTICLE]:
            if len(articles) >= limit:
                break

            try:
                body = self._fetch_pdf_text(notice.pdf_url)
            except (httpx.HTTPError, ArticleContentUnavailableError) as error:
                body_failures.append(error)
                logger.warning(
                    "PDFの取得・抽出に失敗したため記事をスキップ: %s (%s)", notice.pdf_url, error
                )
                continue

            articles.append(
                Article(
                    id=None,
                    source=SOURCE_NAME,
                    url=notice.article_url,
                    title=notice.title,
                    body=body,
                    published_at=notice.published_at,
                )
            )

        if not articles and body_failures:
            raise build_all_bodies_failed_error(SOURCE_NAME, body_failures)
        return articles

    def _fetch_news_rss(self) -> str:
        try:
            response = self._client.get(NEWS_RSS_URL, headers={"User-Agent": USER_AGENT})
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise ArticleSourceUnavailableError(
                source=SOURCE_NAME, reason=f"ニュースRSSの取得に失敗: {error}"
            ) from error
        return response.text

    def _fetch_pdf_text(self, pdf_url: str) -> str:
        response = self._client.get(pdf_url, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        return extract_pdf_text(response.content)
