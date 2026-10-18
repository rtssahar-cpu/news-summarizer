import logging
from datetime import datetime, timedelta, timezone

import pytest

from app.interface_adapters.gateways.khi_news_parser import parse_khi_news_rss
from app.use_cases.errors import SourceStructureChangedError

JST = timezone(timedelta(hours=9))

HTML_ITEM = """
<item>
  <title><![CDATA[船舶の総括操縦システム「KICS<sup>®</sup>」にタグボート向け機能を追加]]></title>
  <link>https://www.khi.co.jp/pressrelease/detail/20261005_1.html</link>
  <category>プレスリリース</category>
  <pubDate>Mon, 5 Oct 2026 15:00:00 +0900</pubDate>
</item>
"""

PDF_ITEM = """
<item>
  <title>組織改正および人事異動について</title>
  <link>https://www.khi.co.jp/pressrelease/news_260929-1.pdf</link>
  <pubDate>Tue,29 Sep 2026 13:30:10 +0900</pubDate>
</item>
"""

IR_ITEM = """
<item>
  <title>グループビジョン2030・進捗報告会（2026年10月6日）</title>
  <link>https://www.khi.co.jp/ir/library/other_presen_261006.html</link>
  <pubDate>Tue, 6 Oct 2026 13:00:00 +0900</pubDate>
</item>
"""

BROKEN_DATE_ITEM = """
<item>
  <title>日付が壊れたニュース</title>
  <link>https://www.khi.co.jp/pressrelease/detail/20261001_1.html</link>
  <pubDate>not a date</pubDate>
</item>
"""


def build_rss(*items: str) -> str:
    return f'<?xml version="1.0"?><rss version="2.0"><channel>{"".join(items)}</channel></rss>'


def test_parse_khi_news_rss_extracts_title_url_and_date() -> None:
    news_list = parse_khi_news_rss(build_rss(HTML_ITEM))

    assert len(news_list) == 1
    news = news_list[0]
    assert news.title == "船舶の総括操縦システム「KICS®」にタグボート向け機能を追加"
    assert news.article_url == "https://www.khi.co.jp/pressrelease/detail/20261005_1.html"
    assert news.published_at == datetime(2026, 10, 5, 15, 0, tzinfo=JST)


def test_parse_khi_news_rss_accepts_pdf_link_and_date_without_space() -> None:
    news_list = parse_khi_news_rss(build_rss(PDF_ITEM))

    assert news_list[0].article_url == "https://www.khi.co.jp/pressrelease/news_260929-1.pdf"
    assert news_list[0].published_at == datetime(2026, 9, 29, 13, 30, 10, tzinfo=JST)


def test_parse_khi_news_rss_skips_non_press_release_item() -> None:
    news_list = parse_khi_news_rss(build_rss(IR_ITEM, HTML_ITEM))

    assert [news.article_url for news in news_list] == [
        "https://www.khi.co.jp/pressrelease/detail/20261005_1.html"
    ]


def test_parse_khi_news_rss_skips_item_with_invalid_date(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        news_list = parse_khi_news_rss(build_rss(BROKEN_DATE_ITEM, HTML_ITEM))

    assert len(news_list) == 1
    assert "日付の形式が不正" in caplog.text


def test_parse_khi_news_rss_raises_when_no_item_found() -> None:
    with pytest.raises(SourceStructureChangedError, match="1件も抽出できません"):
        parse_khi_news_rss(build_rss(IR_ITEM))


def test_parse_khi_news_rss_raises_when_xml_is_malformed() -> None:
    with pytest.raises(SourceStructureChangedError, match="XMLとして解析できません"):
        parse_khi_news_rss("<rss><channel>")
