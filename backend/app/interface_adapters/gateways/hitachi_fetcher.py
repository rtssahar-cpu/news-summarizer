import logging

import httpx

from app.entities.article import Article
from app.interface_adapters.gateways.hitachi_news_parser import (
    BASE_URL,
    SOURCE_NAME,
    parse_hitachi_news_list,
)
from app.interface_adapters.gateways.http_headers import USER_AGENT
from app.interface_adapters.gateways.pdf_text import extract_pdf_text
from app.use_cases.errors import ArticleContentUnavailableError, ArticleSourceUnavailableError

# 一覧ページ（/ja-jp/press/）はJSで描画されるため、裏で読み込んでいるJSON（新しい順に12件）を
# 直接取得する
NEWS_LIST_JSON_URL = (
    f"{BASE_URL}/content/hitachi/global/ja_jp/press/jcr:content/root/main-container/"
    "initial-container/page_search_copy_cop.json"
)

logger = logging.getLogger(__name__)


class HitachiNewsFetcher:
    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def fetch_recent_articles(self, limit: int = 5) -> list[Article]:
        news_list = parse_hitachi_news_list(self._fetch_news_list())
        articles: list[Article] = []

        for news in news_list[:limit]:
            try:
                body = self._fetch_pdf_body(news.pdf_url)
            except (httpx.HTTPError, ArticleContentUnavailableError) as error:
                logger.warning(
                    "記事本文の取得・抽出に失敗したため記事をスキップ: %s (%s)", news.pdf_url, error
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

    def _fetch_news_list(self) -> str:
        try:
            response = self._client.get(NEWS_LIST_JSON_URL, headers={"User-Agent": USER_AGENT})
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise ArticleSourceUnavailableError(
                source=SOURCE_NAME, reason=f"ニュース一覧のJSONの取得に失敗: {error}"
            ) from error
        return response.text

    def _fetch_pdf_body(self, pdf_url: str) -> str:
        # 記事ページには本文がないことが多いため、本文は常にPDFから取得する
        # （PDFはAESで暗号化されている）
        response = self._client.get(pdf_url, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        pdf_text = extract_pdf_text(response.content)
        # 画像だけのPDFはテキストを抽出できず空文字になる
        if not pdf_text:
            raise ArticleContentUnavailableError("PDFからテキストを抽出できません（テキストが空）")
        return pdf_text
