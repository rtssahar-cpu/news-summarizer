import logging

import httpx

from app.entities.article import Article
from app.interface_adapters.gateways.article_body_failures import (
    ArticleBodyFailure,
    build_all_bodies_failed_error,
)
from app.interface_adapters.gateways.http_headers import USER_AGENT
from app.interface_adapters.gateways.nec_article_parser import extract_nec_article_body
from app.interface_adapters.gateways.nec_news_parser import SOURCE_NAME, parse_nec_news_rss
from app.use_cases.errors import ArticleContentUnavailableError, ArticleSourceUnavailableError

# 一覧ページ（/press/）はJSで描画されるが、裏で読み込んでいるのはこのRSS（新しい順に約100件）
NEWS_RSS_URL = "https://jpn.nec.com/ja/press/press.xml"

logger = logging.getLogger(__name__)


class NecPressReleaseFetcher:
    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def fetch_recent_articles(self, limit: int = 5) -> list[Article]:
        news_list = parse_nec_news_rss(self._fetch_news_rss())
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

    def _fetch_news_rss(self) -> str:
        try:
            response = self._client.get(NEWS_RSS_URL, headers={"User-Agent": USER_AGENT})
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise ArticleSourceUnavailableError(
                source=SOURCE_NAME, reason=f"ニュースRSSの取得に失敗: {error}"
            ) from error
        return response.text

    def _fetch_article_body(self, article_url: str) -> str:
        # 添付PDF（受賞者の略歴等の補足資料）は本文と重複・補足する内容のため取得しない
        response = self._client.get(article_url, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        return extract_nec_article_body(response.text)
