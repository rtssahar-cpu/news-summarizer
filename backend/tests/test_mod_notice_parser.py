import logging
from datetime import UTC, datetime

import pytest

from app.interface_adapters.gateways.mod_notice_parser import parse_mod_notice_list
from app.use_cases.errors import SourceStructureChangedError

SAMPLE_HTML = """
<div class="news__item">
    <dt class="date">9/19</dt>
    <dd class="news__title">
        <a href="/j/approach/anpo/2026/0918a_usa-j.html">日米電話会談について</a>
        <a href="/j/approach/anpo/2026/pdf/0918a_usa-j.pdf" target="_blank">印刷用</a>
    </dd>
</div>
<div class="news__item">
    <dt class="date">9/18</dt>
    <dd class="news__title">
        <a href="/j/press/news/2026/09/18a.html">PDFなしのお知らせ</a>
    </dd>
</div>
"""


def test_parse_mod_notice_list_extracts_title_date_and_pdf_url() -> None:
    reference_date = datetime(2026, 9, 20, tzinfo=UTC)

    notices = parse_mod_notice_list(SAMPLE_HTML, reference_date=reference_date)

    assert len(notices) == 2
    first = notices[0]
    assert first.title == "日米電話会談について"
    assert first.article_url == "https://www.mod.go.jp/j/approach/anpo/2026/0918a_usa-j.html"
    assert first.pdf_url == "https://www.mod.go.jp/j/approach/anpo/2026/pdf/0918a_usa-j.pdf"
    assert first.published_at == datetime(2026, 9, 19, tzinfo=UTC)


def test_parse_mod_notice_list_handles_item_without_pdf_link() -> None:
    reference_date = datetime(2026, 9, 20, tzinfo=UTC)

    notices = parse_mod_notice_list(SAMPLE_HTML, reference_date=reference_date)

    assert notices[1].pdf_url is None


def test_parse_mod_notice_list_rolls_back_year_when_date_is_in_the_future() -> None:
    reference_date = datetime(2027, 1, 5, tzinfo=UTC)

    notices = parse_mod_notice_list(SAMPLE_HTML, reference_date=reference_date)

    assert notices[0].published_at == datetime(2026, 9, 19, tzinfo=UTC)


def test_parse_mod_notice_list_skips_item_missing_date_or_title() -> None:
    html = """
    <div class="news__item">
        <dd class="news__title"><a href="/no-date.html">日付なし</a></dd>
    </div>
    <div class="news__item">
        <dt class="date">9/1</dt>
    </div>
    """

    notices = parse_mod_notice_list(
        html + SAMPLE_HTML, reference_date=datetime(2026, 9, 20, tzinfo=UTC)
    )

    assert [notice.title for notice in notices] == ["日米電話会談について", "PDFなしのお知らせ"]


@pytest.mark.parametrize("malformed_date", ["9-19", "2/30", "不明"])
def test_parse_mod_notice_list_skips_item_with_malformed_date(
    malformed_date: str, caplog: pytest.LogCaptureFixture
) -> None:
    html = SAMPLE_HTML.replace("9/19", malformed_date)

    with caplog.at_level(logging.WARNING):
        notices = parse_mod_notice_list(html, reference_date=datetime(2026, 9, 20, tzinfo=UTC))

    assert [notice.title for notice in notices] == ["PDFなしのお知らせ"]
    assert "日付の形式が不正" in caplog.text


def test_parse_mod_notice_list_raises_when_no_notice_is_extracted() -> None:
    html = "<html><body><p>構造が変わったページ</p></body></html>"

    with pytest.raises(SourceStructureChangedError):
        parse_mod_notice_list(html, reference_date=datetime(2026, 9, 20, tzinfo=UTC))
