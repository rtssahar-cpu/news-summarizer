from datetime import UTC, date, datetime
from unittest.mock import MagicMock, create_autospec

import pytest

from app.use_cases.article_summary_reader import ArticleSummaryReader, SummarizedArticle
from app.use_cases.errors import ArticleStorageError
from app.use_cases.list_summarized_articles import JST, SummarizedArticleLister

SUMMARIZED_ARTICLE = SummarizedArticle(
    article_id=1,
    source="mod",
    url="https://www.mod.go.jp/j/press/news/2026/11/18a.html",
    title="お知らせ",
    published_at=datetime(2026, 11, 18, tzinfo=JST),
    summary_text="概要: お知らせ。",
    matched_categories=(),
    mentions_price=False,
    mentions_israel=False,
    summarized_at=datetime(2026, 11, 17, 21, tzinfo=UTC),
)


def make_reader() -> MagicMock:
    reader: MagicMock = create_autospec(ArticleSummaryReader, instance=True)
    reader.list_summarized_between.return_value = (SUMMARIZED_ARTICLE,)
    return reader


def fixed_clock(now: datetime) -> MagicMock:
    return MagicMock(return_value=now)


def test_list_for_reads_from_midnight_to_next_midnight_in_jst() -> None:
    reader = make_reader()

    result = SummarizedArticleLister(reader).list_for(date(2026, 11, 18))

    assert result == (SUMMARIZED_ARTICLE,)
    reader.list_summarized_between.assert_called_once_with(
        datetime(2026, 11, 18, tzinfo=JST), datetime(2026, 11, 19, tzinfo=JST)
    )


@pytest.mark.parametrize(
    ("now", "expected_day"),
    [
        # UTCでは前日でも、JSTでは日付が変わっている
        (datetime(2026, 11, 17, 15, 0, tzinfo=UTC), date(2026, 11, 18)),
        (datetime(2026, 11, 17, 14, 59, tzinfo=UTC), date(2026, 11, 17)),
    ],
)
def test_list_for_uses_today_in_jst_when_day_is_omitted(now: datetime, expected_day: date) -> None:
    reader = make_reader()

    SummarizedArticleLister(reader, clock=fixed_clock(now)).list_for()

    start, _ = reader.list_summarized_between.call_args.args
    assert start == datetime.combine(expected_day, datetime.min.time(), tzinfo=JST)


def test_list_for_propagates_storage_error() -> None:
    reader = make_reader()
    reader.list_summarized_between.side_effect = ArticleStorageError("DBに接続できません")

    with pytest.raises(ArticleStorageError):
        SummarizedArticleLister(reader).list_for(date(2026, 11, 18))


def test_default_clock_returns_current_utc_time() -> None:
    today = SummarizedArticleLister(make_reader()).today()

    assert today == datetime.now(JST).date()
