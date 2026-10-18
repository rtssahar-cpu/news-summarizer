import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from app.interface_adapters.gateways.hitachi_news_parser import parse_hitachi_news_list
from app.use_cases.errors import SourceStructureChangedError

JST = timezone(timedelta(hours=9))


def build_item(
    news_path: str, publish_date: str = "2026-10-16T17:00:00", title: str = "タイトル"
) -> dict[str, Any]:
    return {
        "newsPath": news_path,
        "newsTitle": title,
        "publishDateValue": publish_date,
        "newsPublishDate": "2026年10月16日",
        "displayTags": "エネルギー",
    }


NEWS_ITEM = build_item(
    "https://www.hitachi.com/ja-jp/press/articles/2026/10/1016a/",
    title="日立エナジーとアンサルド・エネルジア、覚書を締結",
)
OTHER_SITE_ITEM = build_item("https://www.hitachi.co.jp/New/cnews/month/2026/10/1016.html")
BROKEN_DATE_ITEM = build_item(
    "https://www.hitachi.com/ja-jp/press/articles/2026/10/1015/", publish_date="2026年10月15日"
)


def build_json(*items: Any) -> str:
    return json.dumps({"total": len(items), "searchPagesList": list(items)}, ensure_ascii=False)


def test_parse_hitachi_news_list_extracts_title_urls_and_date() -> None:
    news_list = parse_hitachi_news_list(build_json(NEWS_ITEM))

    assert len(news_list) == 1
    news = news_list[0]
    assert news.title == "日立エナジーとアンサルド・エネルジア、覚書を締結"
    assert news.article_url == "https://www.hitachi.com/ja-jp/press/articles/2026/10/1016a/"
    assert news.pdf_url == (
        "https://www.hitachi.com/content/dam/hitachi/global/ja_jp/press/files/2026/10/1016a.pdf"
    )
    assert news.published_at == datetime(2026, 10, 16, 17, 0, tzinfo=JST)


def test_parse_hitachi_news_list_skips_non_article_items() -> None:
    news_list = parse_hitachi_news_list(build_json(OTHER_SITE_ITEM, "not a dict", NEWS_ITEM))

    assert [news.article_url for news in news_list] == [NEWS_ITEM["newsPath"]]


def test_parse_hitachi_news_list_skips_item_with_invalid_date(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        news_list = parse_hitachi_news_list(build_json(BROKEN_DATE_ITEM, NEWS_ITEM))

    assert len(news_list) == 1
    assert "日付の形式が不正" in caplog.text


@pytest.mark.parametrize("broken_json", ["<html></html>", "{}", "[]", '{"searchPagesList": 1}'])
def test_parse_hitachi_news_list_raises_when_json_structure_is_unexpected(
    broken_json: str,
) -> None:
    with pytest.raises(SourceStructureChangedError, match="JSONを解析できません"):
        parse_hitachi_news_list(broken_json)


def test_parse_hitachi_news_list_raises_when_no_item_found() -> None:
    with pytest.raises(SourceStructureChangedError, match="1件も抽出できません"):
        parse_hitachi_news_list(build_json(OTHER_SITE_ITEM))
