import logging
import re
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from xml.etree.ElementTree import Element

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import ParseError, fromstring

from app.use_cases.errors import SourceStructureChangedError

SOURCE_NAME = "mhi"
# 例: /jp/news/261008.html、/jp/news/26102001.html（同じ日に複数の発表がある場合）
NEWS_URL_PATTERN = re.compile(r"^https://www\.mhi\.com/jp/news/.+\.html$")

logger = logging.getLogger(__name__)


@dataclass
class MhiNews:
    published_at: datetime
    title: str
    article_url: str


def parse_mhi_news_rss(rss_xml: str) -> list[MhiNews]:
    try:
        root = fromstring(rss_xml)
    except (ParseError, DefusedXmlException) as error:
        raise SourceStructureChangedError(
            source=SOURCE_NAME, reason=f"RSSをXMLとして解析できません: {error}"
        ) from error

    news_list = [news for item in root.iter("item") if (news := _parse_item(item)) is not None]
    if not news_list:
        raise SourceStructureChangedError(
            source=SOURCE_NAME, reason="RSSからニュースを1件も抽出できません"
        )
    return news_list


def _parse_item(item: Element) -> MhiNews | None:
    title_element = item.find("title")
    article_url = item.findtext("link", default="").strip()
    pub_date_text = item.findtext("pubDate", default="").strip()
    if title_element is None or not article_url:
        logger.warning("タイトルまたはリンクがないためニュースをスキップ: %r", article_url)
        return None
    if NEWS_URL_PATTERN.match(article_url) is None:
        # 技術誌（/jp/technology/review/）等はページ構造が異なり、本文を抽出できないため対象外
        logger.debug("ニュース以外の項目のためスキップ: %r", article_url)
        return None

    try:
        published_at = parsedate_to_datetime(pub_date_text)
    except ValueError:
        logger.warning("日付の形式が不正なためニュースをスキップ: %r", pub_date_text)
        return None

    # タイトル内の<br/>で区切られた主題と副題を、空白でつなげて1行にする
    title = " ".join(text.strip() for text in title_element.itertext() if text.strip())
    return MhiNews(published_at=published_at, title=title, article_url=article_url)
