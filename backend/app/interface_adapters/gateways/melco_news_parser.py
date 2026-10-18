import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.use_cases.errors import SourceStructureChangedError

SOURCE_NAME = "melco"
BASE_URL = "https://www.mitsubishielectric.co.jp"
# 一覧のリンク先は記事ページ（/ja/pr/2026/1013_co/）か、PDFのみの発表
# （/ja/pr/2026/pdf/1008_pu.pdf）。記事ページにも同じ内容の「リリース全文」PDF
# （/ja/pr/2026/pdf/1013_co.pdf）があるため、本文は常にPDFから取得する。
# 子会社のサイト等、他サイトへのリンクは対象外
ARTICLE_PATH_PATTERN = re.compile(r"^/ja/pr/(?P<year>\d{4})/(?P<article_id>[\w-]+)/$")
PDF_PATH_PATTERN = re.compile(r"^/ja/pr/\d{4}/pdf/[\w-]+\.pdf$")

logger = logging.getLogger(__name__)


@dataclass
class MelcoNews:
    published_at: datetime
    title: str
    article_url: str
    pdf_url: str


def parse_melco_news_list(json_text: str) -> list[MelcoNews]:
    """一覧ページが裏で読み込むJSON（新しい順）を解析する。"""
    try:
        items = json.loads(json_text)["news"]
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


def _parse_item(item: dict[str, Any]) -> MelcoNews | None:
    path = str(item.get("url", ""))
    if (article_match := ARTICLE_PATH_PATTERN.match(path)) is not None:
        pdf_path = f"/ja/pr/{article_match['year']}/pdf/{article_match['article_id']}.pdf"
    elif PDF_PATH_PATTERN.match(path) is not None:
        pdf_path = path
    else:
        logger.debug("三菱電機のニュースリリース以外の項目のためスキップ: %r", path)
        return None

    # 例: 2026-10-16T19:30:00+09:00（タイムゾーン付き）
    date_text = str(item.get("articlePublishtime", ""))
    try:
        published_at = datetime.fromisoformat(date_text)
    except ValueError:
        logger.warning("日付の形式が不正なためニュースをスキップ: %r", date_text)
        return None
    if published_at.tzinfo is None:
        logger.warning("日付にタイムゾーンがないためニュースをスキップ: %r", date_text)
        return None

    return MelcoNews(
        published_at=published_at,
        title=str(item.get("title", "")).strip(),
        article_url=f"{BASE_URL}{path}",
        pdf_url=f"{BASE_URL}{pdf_path}",
    )
