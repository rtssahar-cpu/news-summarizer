import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from app.interface_adapters.gateways.melco_news_parser import parse_melco_news_list
from app.use_cases.errors import SourceStructureChangedError

JST = timezone(timedelta(hours=9))


def build_item(
    url: str,
    publish_time: str = "2026-10-13T11:00:00+09:00",
    title: str = "タイトル",
    link_type: str = "",
) -> dict[str, Any]:
    return {
        "date": "2026年10月13日",
        "year": "2026",
        "categories": ["経営", "インフラ", "防衛・宇宙システム"],
        "title": title,
        "description": "",
        "url": url,
        "linkType": link_type,
        "articlePublishtime": publish_time,
    }


ARTICLE_ITEM = build_item(
    "/ja/pr/2026/1013_co/", title="国連気候変動枠組条約第31回締約国会議（COP31）に参加"
)
PDF_ITEM = build_item("/ja/pr/2026/pdf/1008_pu.pdf", link_type="pdf")
OTHER_SITE_ITEM = build_item("https://www.mebs.co.jp/press/261006.html", link_type="external")
BROKEN_DATE_ITEM = build_item("/ja/pr/2026/1015_pd/", publish_time="2026年10月15日")
NAIVE_DATE_ITEM = build_item("/ja/pr/2026/1015_pd/", publish_time="2026-10-15T16:00:00")


def build_json(*items: Any) -> str:
    return json.dumps({"news": list(items), "meta": {"count": str(len(items))}}, ensure_ascii=False)


def test_parse_melco_news_list_derives_pdf_url_from_article_url() -> None:
    news_list = parse_melco_news_list(build_json(ARTICLE_ITEM))

    assert len(news_list) == 1
    news = news_list[0]
    assert news.title == "国連気候変動枠組条約第31回締約国会議（COP31）に参加"
    assert news.article_url == "https://www.mitsubishielectric.co.jp/ja/pr/2026/1013_co/"
    assert news.pdf_url == "https://www.mitsubishielectric.co.jp/ja/pr/2026/pdf/1013_co.pdf"
    assert news.published_at == datetime(2026, 10, 13, 11, 0, tzinfo=JST)


def test_parse_melco_news_list_uses_pdf_url_as_is_for_pdf_only_news() -> None:
    news = parse_melco_news_list(build_json(PDF_ITEM))[0]

    assert news.article_url == "https://www.mitsubishielectric.co.jp/ja/pr/2026/pdf/1008_pu.pdf"
    assert news.pdf_url == news.article_url


def test_parse_melco_news_list_skips_other_site_items() -> None:
    news_list = parse_melco_news_list(build_json(OTHER_SITE_ITEM, "not a dict", ARTICLE_ITEM))

    assert [news.article_url for news in news_list] == [
        "https://www.mitsubishielectric.co.jp/ja/pr/2026/1013_co/"
    ]


@pytest.mark.parametrize(
    ("broken_item", "message"),
    [(BROKEN_DATE_ITEM, "日付の形式が不正"), (NAIVE_DATE_ITEM, "タイムゾーンがない")],
)
def test_parse_melco_news_list_skips_item_with_invalid_date(
    caplog: pytest.LogCaptureFixture, broken_item: dict[str, Any], message: str
) -> None:
    with caplog.at_level(logging.WARNING):
        news_list = parse_melco_news_list(build_json(broken_item, ARTICLE_ITEM))

    assert len(news_list) == 1
    assert message in caplog.text


@pytest.mark.parametrize("broken_json", ["<html></html>", "{}", "[]", '{"news": 1}'])
def test_parse_melco_news_list_raises_when_json_structure_is_unexpected(broken_json: str) -> None:
    with pytest.raises(SourceStructureChangedError, match="JSONを解析できません"):
        parse_melco_news_list(broken_json)


def test_parse_melco_news_list_raises_when_no_item_found() -> None:
    with pytest.raises(SourceStructureChangedError, match="1件も抽出できません"):
        parse_melco_news_list(build_json(OTHER_SITE_ITEM))
