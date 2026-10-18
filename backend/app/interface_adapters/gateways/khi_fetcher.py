import logging

import httpx

from app.entities.article import Article
from app.interface_adapters.gateways.http_headers import USER_AGENT
from app.interface_adapters.gateways.khi_article_parser import extract_khi_article_body
from app.interface_adapters.gateways.khi_news_parser import SOURCE_NAME, parse_khi_news_rss
from app.interface_adapters.gateways.pdf_text import extract_pdf_text
from app.use_cases.errors import ArticleContentUnavailableError, ArticleSourceUnavailableError

NEWS_RSS_URL = "https://www.khi.co.jp/pressrelease/rss/pressrelease.xml"

logger = logging.getLogger(__name__)


class KhiPressReleaseFetcher:
    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def fetch_recent_articles(self, limit: int = 5) -> list[Article]:
        news_list = parse_khi_news_rss(self._fetch_news_rss())
        articles: list[Article] = []

        for news in news_list[:limit]:
            try:
                body = self._fetch_article_body(news.article_url)
            except (httpx.HTTPError, ArticleContentUnavailableError) as error:
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
        response = self._client.get(article_url, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        # 記事ページがなくPDFだけで発表されるプレスリリースもある（人事異動・共同発表等）
        if article_url.endswith(".pdf"):
            return _require_non_empty(extract_pdf_text(response.content))
        return extract_khi_article_body(response.text)


def _require_non_empty(pdf_text: str) -> str:
    # 画像だけのPDFはテキストを抽出できず空文字になる
    if not pdf_text:
        raise ArticleContentUnavailableError("PDFからテキストを抽出できません（テキストが空）")
    return pdf_text
