import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from bs4 import BeautifulSoup, Tag

from app.use_cases.errors import SourceStructureChangedError

SOURCE_NAME = "subaru"
BASE_URL = "https://www.subaru.co.jp"
JST = timezone(timedelta(hours=9))
# 一覧の各項目は <li><time>2026/10/05</time>...<p><a href="記事のパス">タイトル</a></p></li>
NEWS_ITEM_SELECTOR = "div.component-newsList li"
# 例: /news/2026_10_05_171759（決算発表は /ir/library/results.html へのリンクのため対象外）
ARTICLE_PATH_PATTERN = re.compile(r"^/news/\d{4}_\d{2}_\d{2}_\d+$")
DATE_PATTERN = re.compile(r"^(\d{4})/(\d{2})/(\d{2})$")

logger = logging.getLogger(__name__)


@dataclass
class SubaruNews:
    published_at: datetime
    title: str
    article_url: str


def parse_subaru_news_list(html: str) -> list[SubaruNews]:
    soup = BeautifulSoup(html, "html.parser")
    news_list = [
        news for item in soup.select(NEWS_ITEM_SELECTOR) if (news := _parse_item(item)) is not None
    ]
    if not news_list:
        raise SourceStructureChangedError(
            source=SOURCE_NAME, reason="ニュース一覧ページからニュースを1件も抽出できません"
        )
    return news_list


def _parse_item(item: Tag) -> SubaruNews | None:
    link = item.select_one("p > a[href]")
    article_path = str(link["href"]) if link is not None else ""
    if link is None or ARTICLE_PATH_PATTERN.match(article_path) is None:
        logger.debug("ニュースリリース以外の項目のためスキップ: %r", article_path)
        return None

    time_tag = item.find("time")
    date_text = time_tag.get_text(strip=True) if time_tag is not None else ""
    date_match = DATE_PATTERN.match(date_text)
    if date_match is None:
        logger.warning("日付の形式が不正なためニュースをスキップ: %r", date_text)
        return None
    year, month, day = (int(part) for part in date_match.groups())

    return SubaruNews(
        published_at=datetime(year, month, day, tzinfo=JST),
        title=link.get_text(strip=True),
        article_url=f"{BASE_URL}{article_path}",
    )
