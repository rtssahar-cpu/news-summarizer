import logging

import httpx

from app.entities.article import Article
from app.interface_adapters.gateways.article_body_failures import (
    ArticleBodyFailure,
    build_all_bodies_failed_error,
)
from app.interface_adapters.gateways.http_headers import USER_AGENT
from app.interface_adapters.gateways.melco_article_parser import extract_melco_split_pdf_urls
from app.interface_adapters.gateways.melco_news_parser import (
    BASE_URL,
    SOURCE_NAME,
    MelcoNews,
    parse_melco_news_list,
)
from app.interface_adapters.gateways.pdf_text import extract_pdf_text
from app.use_cases.errors import ArticleContentUnavailableError, ArticleSourceUnavailableError

# 一覧ページ（/ja/pr/）はJSで描画されるため、裏で読み込んでいるJSON（2023年以降の全件。新しい順）を
# 直接取得する
NEWS_LIST_JSON_URL = (
    f"{BASE_URL}/global/common/mel25/news-data/jws-news/japan/www/ja/news-article.json"
)

logger = logging.getLogger(__name__)


class MelcoNewsFetcher:
    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def fetch_recent_articles(self, limit: int = 5) -> list[Article]:
        news_list = parse_melco_news_list(self._fetch_news_list())
        articles: list[Article] = []
        body_failures: list[ArticleBodyFailure] = []

        for news in news_list[:limit]:
            try:
                body = self._fetch_body(news)
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
            response = self._get(NEWS_LIST_JSON_URL)
        except httpx.HTTPError as error:
            raise ArticleSourceUnavailableError(
                source=SOURCE_NAME, reason=f"ニュース一覧のJSONの取得に失敗: {error}"
            ) from error
        return response.text

    def _fetch_body(self, news: MelcoNews) -> str:
        try:
            return self._fetch_pdf_text(news.pdf_url)
        except httpx.HTTPStatusError as error:
            # PDFのみの発表は導いたURLではないため、404でも分割PDFは探さない
            is_derived_pdf = news.pdf_url != news.article_url
            if error.response.status_code != httpx.codes.NOT_FOUND or not is_derived_pdf:
                raise

        # 決算・子会社化等の記事は「リリース全文」PDFがなく、記事ページに分割されたPDFが並ぶ。
        # 防衛関連の内容を取りこぼさないよう、すべて取得して連結する
        article_html = self._get(news.article_url).text
        split_pdf_urls = extract_melco_split_pdf_urls(article_html, news.pdf_url)
        return "\n".join(self._fetch_pdf_text(pdf_url) for pdf_url in split_pdf_urls)

    def _fetch_pdf_text(self, pdf_url: str) -> str:
        pdf_text = extract_pdf_text(self._get(pdf_url).content)
        # 画像だけのPDFはテキストを抽出できず空文字になる
        if not pdf_text:
            raise ArticleContentUnavailableError("PDFからテキストを抽出できません（テキストが空）")
        return pdf_text

    def _get(self, url: str) -> httpx.Response:
        response = self._client.get(url, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        return response
