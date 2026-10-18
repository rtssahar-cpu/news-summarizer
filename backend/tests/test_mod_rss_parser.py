import logging
from datetime import datetime, timedelta, timezone

import pytest

from app.interface_adapters.gateways.mod_rss_parser import parse_mod_news_rss
from app.use_cases.errors import SourceStructureChangedError

JST = timezone(timedelta(hours=9))

HTML_NOTICE_ITEM = """
<item><title>日マレーシア防衛相会談について</title><link>/j/press/news/2026/10/16c.html</link>
<pubDate>Fri, 16 Oct 2026 18:24:18 +0900</pubDate></item>
"""

PDF_NOTICE_ITEM = """
<item><title>日米合同委員会合意について</title><link>/j/press/news/2026/10/05b.pdf</link>
<pubDate>Mon, 05 Oct 2026 18:09:10 +0900</pubDate></item>
"""

NON_NOTICE_ITEM = """
<item><title>日韓防衛次官級協議について（結果概要）</title>
<link>/j/approach/exchange/area/2026/20261009_kor-j.html</link></item>
"""


def build_rss(*items: str) -> str:
    return f'<?xml version="1.0"?><rss version="2.0"><channel>{"".join(items)}</channel></rss>'


def test_parse_mod_news_rss_extracts_notice_and_guesses_pdf_url() -> None:
    notices = parse_mod_news_rss(build_rss(HTML_NOTICE_ITEM))

    assert len(notices) == 1
    notice = notices[0]
    assert notice.title == "日マレーシア防衛相会談について"
    assert notice.article_url == "https://www.mod.go.jp/j/press/news/2026/10/16c.html"
    assert notice.pdf_url == "https://www.mod.go.jp/j/press/news/2026/10/16c.pdf"
    assert notice.published_at == datetime(2026, 10, 16, tzinfo=JST)


def test_parse_mod_news_rss_uses_pdf_link_as_is() -> None:
    notice = parse_mod_news_rss(build_rss(PDF_NOTICE_ITEM))[0]

    assert notice.article_url == "https://www.mod.go.jp/j/press/news/2026/10/05b.pdf"
    assert notice.pdf_url == "https://www.mod.go.jp/j/press/news/2026/10/05b.pdf"


def test_parse_mod_news_rss_skips_non_notice_item() -> None:
    notices = parse_mod_news_rss(build_rss(NON_NOTICE_ITEM, HTML_NOTICE_ITEM))

    assert [notice.title for notice in notices] == ["日マレーシア防衛相会談について"]


def test_parse_mod_news_rss_skips_item_with_invalid_date_in_url(
    caplog: pytest.LogCaptureFixture,
) -> None:
    invalid_date_item = (
        "<item><title>不正な日付</title><link>/j/press/news/2026/02/30a.html</link></item>"
    )

    with caplog.at_level(logging.WARNING):
        notices = parse_mod_news_rss(build_rss(invalid_date_item, HTML_NOTICE_ITEM))

    assert len(notices) == 1
    assert "URLの日付が不正" in caplog.text


def test_parse_mod_news_rss_raises_when_no_notice_found() -> None:
    with pytest.raises(SourceStructureChangedError, match="1件も抽出できません"):
        parse_mod_news_rss(build_rss(NON_NOTICE_ITEM))


def test_parse_mod_news_rss_raises_when_xml_is_malformed() -> None:
    with pytest.raises(SourceStructureChangedError, match="XMLとして解析できません"):
        parse_mod_news_rss("<rss><channel>")
