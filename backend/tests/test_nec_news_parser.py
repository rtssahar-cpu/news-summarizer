import logging
from datetime import datetime, timedelta, timezone

import pytest

from app.interface_adapters.gateways.nec_news_parser import parse_nec_news_rss
from app.use_cases.errors import SourceStructureChangedError

JST = timezone(timedelta(hours=9))

PRESS_RELEASE_ITEM = """
<item>
  <category>プレスリリース/研究開発/新技術</category>
  <category>プレスリリース/AI</category>
  <link>https://jpn.nec.com/press/202610/20261014_01.html</link>
  <title>NEC、現場画像に小さく写る被害を高精度に把握するVLM技術を開発</title>
  <description>NECは、災害時に自治体などへ集まる現場画像から...</description>
  <pubDate>Wed, 14 Oct 2026 10:00:00 +0900</pubDate>
</item>
"""

SUBSIDIARY_ITEM = """
<item>
  <category>プレスリリース</category>
  <link>https://www.nec-nexs.com/news/press/2026/1016.html</link>
  <title>NECネクサソリューションズとマイクロニティ、業務提携[NECネクサソリューションズ]</title>
  <pubDate>Fri, 16 Oct 2026 10:00:00 +0900</pubDate>
</item>
"""

BROKEN_DATE_ITEM = """
<item>
  <link>https://jpn.nec.com/press/202610/20261013_01.html</link>
  <title>日付が壊れたニュース</title>
  <pubDate>not a date</pubDate>
</item>
"""


def build_rss(*items: str) -> str:
    return f'<?xml version="1.0"?><rss version="2.0"><channel>{"".join(items)}</channel></rss>'


def test_parse_nec_news_rss_extracts_title_url_and_date() -> None:
    news_list = parse_nec_news_rss(build_rss(PRESS_RELEASE_ITEM))

    assert len(news_list) == 1
    news = news_list[0]
    assert news.title == "NEC、現場画像に小さく写る被害を高精度に把握するVLM技術を開発"
    assert news.article_url == "https://jpn.nec.com/press/202610/20261014_01.html"
    assert news.published_at == datetime(2026, 10, 14, 10, 0, tzinfo=JST)


def test_parse_nec_news_rss_skips_subsidiary_item() -> None:
    news_list = parse_nec_news_rss(build_rss(SUBSIDIARY_ITEM, PRESS_RELEASE_ITEM))

    assert [news.article_url for news in news_list] == [
        "https://jpn.nec.com/press/202610/20261014_01.html"
    ]


def test_parse_nec_news_rss_skips_item_with_invalid_date(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        news_list = parse_nec_news_rss(build_rss(BROKEN_DATE_ITEM, PRESS_RELEASE_ITEM))

    assert len(news_list) == 1
    assert "日付の形式が不正" in caplog.text


def test_parse_nec_news_rss_raises_when_no_item_found() -> None:
    with pytest.raises(SourceStructureChangedError, match="1件も抽出できません"):
        parse_nec_news_rss(build_rss(SUBSIDIARY_ITEM))


def test_parse_nec_news_rss_raises_when_xml_is_malformed() -> None:
    with pytest.raises(SourceStructureChangedError, match="XMLとして解析できません"):
        parse_nec_news_rss("<rss><channel>")
