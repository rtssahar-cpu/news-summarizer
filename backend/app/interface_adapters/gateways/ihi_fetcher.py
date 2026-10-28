import logging

import httpx

from app.entities.article import Article
from app.interface_adapters.gateways.article_body_failures import (
    ArticleBodyFailure,
    build_all_bodies_failed_error,
)
from app.interface_adapters.gateways.http_headers import USER_AGENT
from app.interface_adapters.gateways.ihi_article_parser import extract_ihi_article_body
from app.interface_adapters.gateways.ihi_news_parser import (
    BASE_URL,
    SOURCE_NAME,
    parse_ihi_news_list,
)
from app.use_cases.errors import ArticleContentUnavailableError, ArticleSourceUnavailableError

# RSSがないため、一覧ページ（今年度のニュースが新しい順に並ぶ）を解析する
NEWS_LIST_URL = f"{BASE_URL}/all_news/"

logger = logging.getLogger(__name__)


class IhiNewsFetcher:
    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def fetch_recent_articles(self, limit: int = 5) -> list[Article]:
        news_list = parse_ihi_news_list(self._fetch_news_list())
        articles: list[Article] = []
        body_failures: list[ArticleBodyFailure] = []

        for news in news_list[:limit]:
            try:
                body = self._fetch_article_body(news.article_url)
            except (httpx.HTTPError, ArticleContentUnavailableError) as error:
                body_failures.append(error)
                logger.warning(
                    "記事本文の取得・抽出に失敗したため記事をスキップ: %s (%s)",
                    news.article_url,
                    error,
                )
                continue

            articles.append(
                Article(
                    id=None,
                    source=SOURCE_NAME,
                    url=news.article_url,
                    title=news.title,
                    body=body,
                    published_at=news.published_at,
                )
            )

        if not articles and body_failures:
            raise build_all_bodies_failed_error(SOURCE_NAME, body_failures)
        return articles

    def _fetch_news_list(self) -> str:
        try:
            response = self._client.get(NEWS_LIST_URL, headers={"User-Agent": USER_AGENT})
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise ArticleSourceUnavailableError(
                source=SOURCE_NAME, reason=f"ニュース一覧ページの取得に失敗: {error}"
            ) from error
        return response.text

    def _fetch_article_body(self, article_url: str) -> str:
        response = self._client.get(article_url, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        return extract_ihi_article_body(response.text)
