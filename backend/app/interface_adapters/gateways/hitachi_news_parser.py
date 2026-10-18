import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from app.use_cases.errors import SourceStructureChangedError

SOURCE_NAME = "hitachi"
BASE_URL = "https://www.hitachi.com"
JST = timezone(timedelta(hours=9))
# 例: https://www.hitachi.com/ja-jp/press/articles/2026/10/1016a/
# 記事ページには本文がなく（日付・タイトル・PDFへのリンクのみ）、本文はPDFにしかないことが多いため、
# 記事URLからPDFのURL（/content/dam/hitachi/global/ja_jp/press/files/2026/10/1016a.pdf）を導く
ARTICLE_URL_PATTERN = re.compile(
    rf"^{re.escape(BASE_URL)}/ja-jp/press/articles/(?P<article_id>\d{{4}}/\d{{2}}/\d{{4}}[a-z]?)/$"
)
PDF_URL_TEMPLATE = f"{BASE_URL}/content/dam/hitachi/global/ja_jp/press/files/{{article_id}}.pdf"

logger = logging.getLogger(__name__)


@dataclass
class HitachiNews:
    published_at: datetime
    title: str
    article_url: str
    pdf_url: str


def parse_hitachi_news_list(json_text: str) -> list[HitachiNews]:
    """一覧ページが裏で読み込むJSON（新しい順）を解析する。"""
    try:
        items = json.loads(json_text)["searchPagesList"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise SourceStructureChangedError(
            source=SOURCE_NAME, reason=f"ニュース一覧のJSONを解析できません: {error!r}"
        ) from error
    if not isinstance(items, list):
        raise SourceStructureChangedError(
            source=SOURCE_NAME, reason=f"ニュース一覧のJSONを解析できません: {items!r}"
        )

    news_list = [
        news for item in items if isinstance(item, dict) and (news := _parse_item(item)) is not None
    ]
    if not news_list:
        raise SourceStructureChangedError(
            source=SOURCE_NAME, reason="ニュース一覧のJSONからニュースを1件も抽出できません"
        )
    return news_list


def _parse_item(item: dict[str, Any]) -> HitachiNews | None:
    article_url = str(item.get("newsPath", ""))
    url_match = ARTICLE_URL_PATTERN.match(article_url)
    if url_match is None:
        logger.debug("ニュース記事以外の項目のためスキップ: %r", article_url)
        return None

    # 例: 2026-10-16T17:00:00（タイムゾーンなし。日本時間）
    date_text = str(item.get("publishDateValue", ""))
    try:
        published_at = datetime.fromisoformat(date_text).replace(tzinfo=JST)
    except ValueError:
        logger.warning("日付の形式が不正なためニュースをスキップ: %r", date_text)
        return None

    return HitachiNews(
        published_at=published_at,
        title=str(item.get("newsTitle", "")).strip(),
        article_url=article_url,
        pdf_url=PDF_URL_TEMPLATE.format(article_id=url_match["article_id"]),
    )
