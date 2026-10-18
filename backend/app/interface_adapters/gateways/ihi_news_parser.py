import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from bs4 import BeautifulSoup, Tag

from app.use_cases.errors import SourceStructureChangedError

SOURCE_NAME = "ihi"
BASE_URL = "https://www.ihi.co.jp"
JST = timezone(timedelta(hours=9))
# 一覧ページはタブ構成で、種別ごとのタブ（#tab02〜）にも同じニュースが重複して載るため、
# 「すべて」のタブ（#tab01）だけを見る。
# 各項目は <li>...<time>2026年10月07日</time>...<p><a href="記事のパス">タイトル</a></p>...</li>
NEWS_ITEM_SELECTOR = "div#tab01 ul.m-news > li"
# 例: /all_news/2026/aeroengine_space_defense/1202146_13805.html
# （適時開示のPDFや、IR・研究開発のページへのリンクは対象外）
ARTICLE_PATH_PATTERN = re.compile(r"^/all_news/\d{4}/[a-z_]+/\d+_\d+\.html$")
# <time> の datetime 属性は 2022-10-19 のような誤った値のことがあるため、表示テキストを使う
DATE_PATTERN = re.compile(r"^(\d{4})年(\d{2})月(\d{2})日$")

logger = logging.getLogger(__name__)


@dataclass
class IhiNews:
    published_at: datetime
    title: str
    article_url: str


def parse_ihi_news_list(html: str) -> list[IhiNews]:
    soup = BeautifulSoup(html, "html.parser")
    news_list = [
        news for item in soup.select(NEWS_ITEM_SELECTOR) if (news := _parse_item(item)) is not None
    ]
    if not news_list:
        raise SourceStructureChangedError(
            source=SOURCE_NAME, reason="ニュース一覧ページからニュースを1件も抽出できません"
        )
    return news_list


def _parse_item(item: Tag) -> IhiNews | None:
    link = item.select_one("div.m-news_text > p > a[href]")
    article_path = str(link["href"]) if link is not None else ""
    if link is None or ARTICLE_PATH_PATTERN.match(article_path) is None:
        logger.debug("ニュース記事以外の項目のためスキップ: %r", article_path)
        return None

    time_tag = item.find("time")
    date_text = time_tag.get_text(strip=True) if time_tag is not None else ""
    date_match = DATE_PATTERN.match(date_text)
    if date_match is None:
        logger.warning("日付の形式が不正なためニュースをスキップ: %r", date_text)
        return None
    year, month, day = (int(part) for part in date_match.groups())

    return IhiNews(
        published_at=datetime(year, month, day, tzinfo=JST),
        title=link.get_text(strip=True),
        article_url=f"{BASE_URL}{article_path}",
    )
