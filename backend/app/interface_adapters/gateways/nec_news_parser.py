import logging
import re
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from xml.etree.ElementTree import Element

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import ParseError, fromstring

from app.use_cases.errors import SourceStructureChangedError

SOURCE_NAME = "nec"
# 例: https://jpn.nec.com/press/202610/20261014_01.html
# RSSには子会社（NECネクサソリューションズ等。他ドメイン）の発表も含まれるが、
# 防衛関連をほぼ含まないため対象外
PRESS_RELEASE_URL_PATTERN = re.compile(r"^https://jpn\.nec\.com/press/\d{6}/\d{8}_\d{2}\.html$")

logger = logging.getLogger(__name__)


@dataclass
class NecNews:
    published_at: datetime
    title: str
    article_url: str


def parse_nec_news_rss(rss_xml: str) -> list[NecNews]:
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


def _parse_item(item: Element) -> NecNews | None:
    title = item.findtext("title", default="").strip()
    article_url = item.findtext("link", default="").strip()
    if not title or PRESS_RELEASE_URL_PATTERN.match(article_url) is None:
        logger.debug("NEC本体のプレスリリース以外の項目のためスキップ: %r", article_url)
        return None

    pub_date_text = item.findtext("pubDate", default="").strip()
    try:
        published_at = parsedate_to_datetime(pub_date_text)
    except ValueError:
        logger.warning("日付の形式が不正なためニュースをスキップ: %r", pub_date_text)
        return None

    return NecNews(published_at=published_at, title=title, article_url=article_url)
