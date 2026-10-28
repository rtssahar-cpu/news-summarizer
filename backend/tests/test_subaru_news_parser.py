import logging
from datetime import datetime, timedelta, timezone

import pytest

from app.interface_adapters.gateways.subaru_news_parser import parse_subaru_news_list
from app.use_cases.errors import SourceStructureChangedError

JST = timezone(timedelta(hours=9))

NEWS_ITEM = """
<li class="">
  <time>2025/07/09</time>
  <span class="category--aerospace">航空宇宙カンパニー</span>
  <p><a href="/news/2025_07_09_152748">SUBARU　防衛装備庁へ遠隔操作型支援機の実験機を納入</a></p>
</li>
"""

IR_ITEM = """
<li class="">
  <time>2026/08/04</time>
  <span class="category--finance">経営・財務</span>
  <p><a href="/ir/library/results.html">2027年3月期　第1四半期決算を発表</a></p>
</li>
"""

BROKEN_DATE_ITEM = """
<li class="">
  <time>2026年10月1日</time>
  <p><a href="/news/2026_10_01_144908">日付が壊れたニュース</a></p>
</li>
"""


def build_page(*items: str) -> str:
    return f'<div class="component-newsList"><div><ul>{"".join(items)}</ul></div></div>'


def test_parse_subaru_news_list_extracts_title_url_and_date() -> None:
    news_list = parse_subaru_news_list(build_page(NEWS_ITEM))

    assert len(news_list) == 1
    news = news_list[0]
    assert news.title == "SUBARU　防衛装備庁へ遠隔操作型支援機の実験機を納入"
    assert news.article_url == "https://www.subaru.co.jp/news/2025_07_09_152748/"
    assert news.published_at == datetime(2025, 7, 9, tzinfo=JST)


def test_parse_subaru_news_list_skips_non_news_release_item() -> None:
    news_list = parse_subaru_news_list(build_page(IR_ITEM, NEWS_ITEM))

    assert [news.article_url for news in news_list] == [
        "https://www.subaru.co.jp/news/2025_07_09_152748/"
    ]


def test_parse_subaru_news_list_skips_item_with_invalid_date(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        news_list = parse_subaru_news_list(build_page(BROKEN_DATE_ITEM, NEWS_ITEM))

    assert len(news_list) == 1
    assert "日付の形式が不正" in caplog.text


def test_parse_subaru_news_list_raises_when_no_item_found() -> None:
    with pytest.raises(SourceStructureChangedError, match="1件も抽出できません"):
        parse_subaru_news_list(build_page(IR_ITEM))


def test_parse_subaru_news_list_accepts_path_with_trailing_slash() -> None:
    item = NEWS_ITEM.replace('"/news/2025_07_09_152748"', '"/news/2025_07_09_152748/"')

    news_list = parse_subaru_news_list(build_page(item))

    assert news_list[0].article_url == "https://www.subaru.co.jp/news/2025_07_09_152748/"
