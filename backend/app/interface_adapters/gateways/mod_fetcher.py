import logging
from datetime import UTC, datetime

import httpx

from app.entities.article import Article
from app.interface_adapters.gateways.mod_notice_parser import parse_notice_list
from app.interface_adapters.gateways.pdf_text import extract_pdf_text

NOTICE_LIST_URL = "https://www.mod.go.jp/j/press/news/index.html"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

logger = logging.getLogger(__name__)


class ModPressReleaseFetcher:
    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def fetch_recent_articles(self, limit: int = 5) -> list[Article]:
        response = self._client.get(NOTICE_LIST_URL, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()

        notices = parse_notice_list(response.text, reference_date=datetime.now(UTC))
        articles: list[Article] = []

        for notice in notices[:limit]:
            if notice.pdf_url is None:
                logger.warning("PDFリンクが見つからないため記事をスキップ: %s", notice.article_url)
                continue

            try:
                body = self._fetch_pdf_text(notice.pdf_url)
            except httpx.HTTPError:
                logger.warning("PDF取得に失敗したため記事をスキップ: %s", notice.pdf_url)
                continue

            articles.append(
                Article(
                    id=None,
                    source="mod",
                    url=notice.article_url,
                    title=notice.title,
                    body=body,
                    published_at=notice.published_at,
                )
            )

        return articles

    def _fetch_pdf_text(self, pdf_url: str) -> str:
        response = self._client.get(pdf_url, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        return extract_pdf_text(response.content)
