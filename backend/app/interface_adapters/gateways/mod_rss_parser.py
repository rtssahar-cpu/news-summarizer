import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from xml.etree.ElementTree import Element

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import ParseError, fromstring

from app.use_cases.errors import SourceStructureChangedError

SOURCE_NAME = "mod"
MOD_BASE_URL = "https://www.mod.go.jp"
JST = timezone(timedelta(hours=9))
# 例: /j/press/news/2026/10/16e.html（2026/10/16のお知らせ）。PDFへ直接リンクする場合もある
NOTICE_PATH_PATTERN = re.compile(r"^/j/press/news/(\d{4})/(\d{2})/(\d{2})[a-z]+\.(html|pdf)$")

logger = logging.getLogger(__name__)


@dataclass
class ModNotice:
    published_at: datetime
    title: str
    article_url: str
    pdf_url: str


def parse_mod_news_rss(rss_xml: str) -> list[ModNotice]:
    try:
        root = fromstring(rss_xml)
    except (ParseError, DefusedXmlException) as error:
        raise SourceStructureChangedError(
            source=SOURCE_NAME, reason=f"RSSをXMLとして解析できません: {error}"
        ) from error

    notices = [notice for item in root.iter("item") if (notice := _parse_item(item)) is not None]
    if not notices:
        raise SourceStructureChangedError(
            source=SOURCE_NAME, reason="RSSからお知らせを1件も抽出できません"
        )
    return notices


def _parse_item(item: Element) -> ModNotice | None:
    title = item.findtext("title", default="").strip()
    path = item.findtext("link", default="").strip()
    path_match = NOTICE_PATH_PATTERN.match(path)
    if not title or path_match is None:
        # 「お知らせ」以外のページ（/j/approach/ 等）はブロックされ本文を取得できないため対象外
        logger.debug("お知らせ以外の項目のためスキップ: %r", path)
        return None

    year, month, day, extension = path_match.groups()
    try:
        # pubDateはRSSの更新時刻で発表日とずれるため、URLに含まれる日付を発表日とする
        published_at = datetime(int(year), int(month), int(day), tzinfo=JST)
    except ValueError:
        logger.warning("URLの日付が不正なためお知らせをスキップ: %r", path)
        return None

    # PDF版（印刷用）は記事ページと同じパスで拡張子が .pdf のことが多い（ない場合は取得時に404）
    pdf_path = path if extension == "pdf" else path.removesuffix(".html") + ".pdf"
    return ModNotice(
        published_at=published_at,
        title=title,
        article_url=MOD_BASE_URL + path,
        pdf_url=MOD_BASE_URL + pdf_path,
    )
