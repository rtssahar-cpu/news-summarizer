import logging
from datetime import datetime, timedelta, timezone

import pytest

from app.interface_adapters.gateways.ihi_news_parser import parse_ihi_news_list
from app.use_cases.errors import SourceStructureChangedError

JST = timezone(timedelta(hours=9))


def build_item(date_text: str, href: str | None, title: str = "タイトル") -> str:
    link = f'<p><a href="{href}">{title}</a></p>' if href is not None else "<p>本文の抜粋</p>"
    return f"""
<li class="has-news-release has-aviation">
  <div class="m-news_inner">
    <div class="m-news_text">
      <div class="m-news_items"><time datetime="2022-10-19">{date_text}</time></div>
      {link}
    </div>
  </div>
</li>
"""


NEWS_ITEM = build_item(
    "2026年07月22日",
    "/all_news/2026/aeroengine_space_defense/1202146_13805.html",
    "SAR衛星の国内組立・試験能力習得に向けてトレーニングを開始",
)
PDF_ITEM = build_item("2026年09月29日", "/all_news/2026/ir/__icsFiles/afieldfile/2026/09/29/n.pdf")
IR_PAGE_ITEM = build_item("2026年08月05日", "/ir/event/statements_meeting/")
NO_LINK_ITEM = build_item("2026年10月09日", None)
BROKEN_DATE_ITEM = build_item("2026/10/07", "/all_news/2026/other/1202210_13803.html")


def build_page(*items: str, other_tab_items: tuple[str, ...] = ()) -> str:
    return f"""
<div id="tab01"><ul class="m-news">{"".join(items)}</ul></div>
<div id="tab02"><ul class="m-news">{"".join(other_tab_items)}</ul></div>
"""


def test_parse_ihi_news_list_extracts_title_url_and_date_from_text() -> None:
    news_list = parse_ihi_news_list(build_page(NEWS_ITEM))

    assert len(news_list) == 1
    news = news_list[0]
    assert news.title == "SAR衛星の国内組立・試験能力習得に向けてトレーニングを開始"
    assert news.article_url == (
        "https://www.ihi.co.jp/all_news/2026/aeroengine_space_defense/1202146_13805.html"
    )
    # datetime属性（2022-10-19）ではなく表示テキストの日付を使う
    assert news.published_at == datetime(2026, 7, 22, tzinfo=JST)


def test_parse_ihi_news_list_ignores_duplicated_items_in_other_tabs() -> None:
    news_list = parse_ihi_news_list(build_page(NEWS_ITEM, other_tab_items=(NEWS_ITEM,)))

    assert len(news_list) == 1


def test_parse_ihi_news_list_skips_non_article_items() -> None:
    news_list = parse_ihi_news_list(build_page(PDF_ITEM, IR_PAGE_ITEM, NO_LINK_ITEM, NEWS_ITEM))

    assert [news.title for news in news_list] == [
        "SAR衛星の国内組立・試験能力習得に向けてトレーニングを開始"
    ]


def test_parse_ihi_news_list_skips_item_with_invalid_date(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        news_list = parse_ihi_news_list(build_page(BROKEN_DATE_ITEM, NEWS_ITEM))

    assert len(news_list) == 1
    assert "日付の形式が不正" in caplog.text


def test_parse_ihi_news_list_raises_when_no_item_found() -> None:
    with pytest.raises(SourceStructureChangedError, match="1件も抽出できません"):
        parse_ihi_news_list(build_page(PDF_ITEM, other_tab_items=(NEWS_ITEM,)))
