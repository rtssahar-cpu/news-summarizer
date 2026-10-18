import logging
import re
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from xml.etree.ElementTree import Element

from bs4 import BeautifulSoup
from defusedxml import DefusedXmlException
from defusedxml.ElementTree import ParseError, fromstring

from app.use_cases.errors import SourceStructureChangedError

SOURCE_NAME = "khi"
# 例: /pressrelease/detail/20261008_1.html（記事ページ）、/pressrelease/news_261014-1.pdf（PDFのみ）
PRESS_RELEASE_URL_PATTERN = re.compile(r"^https://www\.khi\.co\.jp/pressrelease/.+\.(html|pdf)$")

logger = logging.getLogger(__name__)


@dataclass
class KhiNews:
    published_at: datetime
    title: str
    article_url: str


def parse_khi_news_rss(rss_xml: str) -> list[KhiNews]:
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


def _parse_item(item: Element) -> KhiNews | None:
    # タイトルはCDATA内に<sup>等のHTMLタグを含むことがあるため、タグを除いたテキストにする
    title = BeautifulSoup(item.findtext("title", default=""), "html.parser").get_text().strip()
    article_url = item.findtext("link", default="").strip()
    if not title or PRESS_RELEASE_URL_PATTERN.match(article_url) is None:
        # IR資料（/ir/library/ 等）はページ構造が異なり、装備品に関する情報もほぼないため対象外
        logger.debug("プレスリリース以外の項目のためスキップ: %r", article_url)
        return None

    pub_date_text = item.findtext("pubDate", default="").strip()
    try:
        published_at = parsedate_to_datetime(pub_date_text)
    except ValueError:
        logger.warning("日付の形式が不正なためニュースをスキップ: %r", pub_date_text)
        return None

    return KhiNews(published_at=published_at, title=title, article_url=article_url)
