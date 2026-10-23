from datetime import UTC, datetime
from unittest.mock import MagicMock, create_autospec

import pytest

from app.entities.article import Article
from app.entities.article_analysis import ArticleAnalysis
from app.entities.category import Category
from app.use_cases.article_analyzer import ArticleAnalyzer
from app.use_cases.article_repository import ArticleRepository
from app.use_cases.errors import (
    ArticleAnalysisRequestError,
    ArticleAnalysisUnavailableError,
    ArticleStorageError,
)
from app.use_cases.process_article import ArticleOutcome, ArticleProcessor

ARTICLE = Article(
    id=None,
    source="mhi",
    url="https://www.mhi.com/jp/news/261016.html",
    title="防衛装備庁と契約を締結",
    body="三菱重工業は、防衛装備庁と契約を締結した。",
    published_at=datetime(2026, 10, 16, tzinfo=UTC),
)
ANALYSIS = ArticleAnalysis(
    summary_text="概要: 防衛装備庁と契約を締結した。",
    matched_categories=(Category.CONTRACTOR_MITSUBISHI_HEAVY,),
    mentions_price=False,
    mentions_israel=False,
)


def make_processor(*, stored: bool) -> tuple[ArticleProcessor, MagicMock, MagicMock]:
    analyzer: MagicMock = create_autospec(ArticleAnalyzer, instance=True)
    analyzer.analyze.return_value = ANALYSIS
    repository: MagicMock = create_autospec(ArticleRepository, instance=True)
    repository.exists_by_url.return_value = stored
    return ArticleProcessor(analyzer, repository), analyzer, repository


def test_process_analyzes_and_saves_new_article() -> None:
    processor, analyzer, repository = make_processor(stored=False)

    assert processor.process(ARTICLE) is ArticleOutcome.SAVED
    analyzer.analyze.assert_called_once_with(ARTICLE)
    repository.save_with_analysis.assert_called_once_with(ARTICLE, ANALYSIS)


def test_process_skips_stored_article_without_analyzing() -> None:
    processor, analyzer, repository = make_processor(stored=True)

    assert processor.process(ARTICLE) is ArticleOutcome.ALREADY_STORED
    repository.exists_by_url.assert_called_once_with(ARTICLE.url)
    analyzer.analyze.assert_not_called()
    repository.save_with_analysis.assert_not_called()


def test_process_does_not_save_article_that_cannot_be_analyzed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    processor, analyzer, repository = make_processor(stored=False)
    analyzer.analyze.side_effect = ArticleAnalysisUnavailableError(ARTICLE.url, "refusal")

    assert processor.process(ARTICLE) is ArticleOutcome.ANALYSIS_FAILED
    repository.save_with_analysis.assert_not_called()
    assert "refusal" in caplog.text


@pytest.mark.parametrize(
    ("target", "error"),
    [
        ("analyze", ArticleAnalysisRequestError("認証エラー")),
        ("save_with_analysis", ArticleStorageError("接続できません")),
    ],
)
def test_process_propagates_errors_that_affect_every_article(target: str, error: Exception) -> None:
    processor, analyzer, repository = make_processor(stored=False)
    mock = analyzer if target == "analyze" else repository
    getattr(mock, target).side_effect = error

    with pytest.raises(type(error)):
        processor.process(ARTICLE)
