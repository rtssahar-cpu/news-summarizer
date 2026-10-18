import logging
from datetime import datetime, timedelta, timezone

import pytest

from app.interface_adapters.gateways.mhi_news_parser import parse_mhi_news_rss
from app.use_cases.errors import SourceStructureChangedError

JST = timezone(timedelta(hours=9))

SAMPLE_ITEM = """
<item>
  <title>防衛省向け潜水艦「しょうげい」の進水式を実施<br/>「たいげい」型の8番艦</title>
  <link>https://www.mhi.com/jp/news/261008.html</link>
  <category domain="https://www.mhi.com/jp/news/pressrelease">プレスリリース</category>
  <pubDate>Thu, 08 Oct 2026 11:00:00 +0900</pubDate>
</item>
"""

BROKEN_DATE_ITEM = """
<item>
  <title>日付が壊れたニュース</title>
  <link>https://www.mhi.com/jp/news/261007.html</link>
  <pubDate>not a date</pubDate>
</item>
"""


def build_rss(*items: str) -> str:
    return f'<?xml version="1.0"?><rss version="2.0"><channel>{"".join(items)}</channel></rss>'


def test_parse_mhi_news_rss_extracts_title_url_and_date() -> None:
    news_list = parse_mhi_news_rss(build_rss(SAMPLE_ITEM))

    assert len(news_list) == 1
    news = news_list[0]
    assert news.title == "防衛省向け潜水艦「しょうげい」の進水式を実施 「たいげい」型の8番艦"
    assert news.article_url == "https://www.mhi.com/jp/news/261008.html"
    assert news.published_at == datetime(2026, 10, 8, 11, 0, tzinfo=JST)


def test_parse_mhi_news_rss_skips_item_with_invalid_date(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        news_list = parse_mhi_news_rss(build_rss(BROKEN_DATE_ITEM, SAMPLE_ITEM))

    assert [news.article_url for news in news_list] == ["https://www.mhi.com/jp/news/261008.html"]
    assert "日付の形式が不正" in caplog.text


def test_parse_mhi_news_rss_skips_item_without_link() -> None:
    item_without_link = "<item><title>リンクなし</title></item>"

    news_list = parse_mhi_news_rss(build_rss(item_without_link, SAMPLE_ITEM))

    assert len(news_list) == 1


def test_parse_mhi_news_rss_raises_when_no_item_found() -> None:
    with pytest.raises(SourceStructureChangedError, match="1件も抽出できません"):
        parse_mhi_news_rss(build_rss())


def test_parse_mhi_news_rss_raises_when_xml_is_malformed() -> None:
    with pytest.raises(SourceStructureChangedError, match="XMLとして解析できません"):
        parse_mhi_news_rss("<rss><channel>")
