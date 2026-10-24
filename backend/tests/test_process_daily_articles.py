from datetime import UTC, datetime
from unittest.mock import MagicMock, create_autospec

import pytest

from app.entities.article import Article
from app.use_cases.article_fetcher import ArticleFetcher
from app.use_cases.errors import (
    ArticleSourceUnavailableError,
    ArticleStorageError,
    SourceStructureChangedError,
)
from app.use_cases.process_article import ArticleOutcome, ArticleProcessor
from app.use_cases.process_daily_articles import DailyArticleProcessor, SourceResult, count_outcomes


def make_article(source: str, number: int) -> Article:
    return Article(
        id=None,
        source=source,
        url=f"https://example.com/{source}/{number}.html",
        title=f"記事{number}",
        body="本文",
        published_at=datetime(2026, 10, 23, tzinfo=UTC),
    )


def make_fetcher(
    articles: list[Article] | None = None, error: Exception | None = None
) -> MagicMock:
    fetcher: MagicMock = create_autospec(ArticleFetcher, instance=True)
    fetcher.fetch_recent_articles.return_value = articles or []
    fetcher.fetch_recent_articles.side_effect = error
    return fetcher


def make_processor(*outcomes: ArticleOutcome) -> MagicMock:
    processor: MagicMock = create_autospec(ArticleProcessor, instance=True)
    processor.process.side_effect = list(outcomes)
    return processor


def test_count_outcomes_includes_outcomes_with_zero_articles() -> None:
    assert count_outcomes([ArticleOutcome.SAVED, ArticleOutcome.SAVED]) == {
        ArticleOutcome.SAVED: 2,
        ArticleOutcome.ALREADY_STORED: 0,
        ArticleOutcome.ANALYSIS_FAILED: 0,
    }


def test_run_processes_every_article_and_counts_outcomes_per_source(
    caplog: pytest.LogCaptureFixture,
) -> None:
    mod_articles = [make_article("mod", 1), make_article("mod", 2)]
    mhi_articles = [make_article("mhi", 1)]
    fetchers = {"mod": make_fetcher(mod_articles), "mhi": make_fetcher(mhi_articles)}
    processor = make_processor(
        ArticleOutcome.SAVED, ArticleOutcome.ALREADY_STORED, ArticleOutcome.ANALYSIS_FAILED
    )
    caplog.set_level("INFO")

    results = DailyArticleProcessor(fetchers, processor, articles_per_source=3).run()

    assert results == (
        SourceResult("mod", count_outcomes([ArticleOutcome.SAVED, ArticleOutcome.ALREADY_STORED])),
        SourceResult("mhi", count_outcomes([ArticleOutcome.ANALYSIS_FAILED])),
    )
    fetchers["mod"].fetch_recent_articles.assert_called_once_with(3)
    processed_articles = [call.args[0] for call in processor.process.call_args_list]
    assert processed_articles == mod_articles + mhi_articles
    assert "saved=1, already_stored=1, analysis_failed=0" in caplog.text


@pytest.mark.parametrize(
    ("error", "log_level"),
    [
        (ArticleSourceUnavailableError("mod", "503"), "WARNING"),
        (SourceStructureChangedError("mod", "一覧が見つかりません"), "ERROR"),
    ],
)
def test_run_skips_only_the_source_that_cannot_be_fetched(
    error: ArticleSourceUnavailableError | SourceStructureChangedError,
    log_level: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    fetchers = {"mod": make_fetcher(error=error), "mhi": make_fetcher([make_article("mhi", 1)])}
    processor = make_processor(ArticleOutcome.SAVED)

    results = DailyArticleProcessor(fetchers, processor).run()

    assert results == (
        SourceResult("mod", count_outcomes([]), fetch_error=error),
        SourceResult("mhi", count_outcomes([ArticleOutcome.SAVED])),
    )
    assert [record.levelname for record in caplog.records] == [log_level]


def test_run_propagates_errors_that_affect_every_article() -> None:
    fetchers = {"mod": make_fetcher([make_article("mod", 1)]), "mhi": make_fetcher()}
    processor = make_processor()
    processor.process.side_effect = ArticleStorageError("接続できません")

    with pytest.raises(ArticleStorageError):
        DailyArticleProcessor(fetchers, processor).run()
    fetchers["mhi"].fetch_recent_articles.assert_not_called()
