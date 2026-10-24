import logging
from unittest.mock import MagicMock, create_autospec

import httpx
import pytest

from app.frameworks import daily_job
from app.frameworks.daily_job import (
    EXIT_FAILURE,
    EXIT_SUCCESS,
    build_fetchers,
    decide_exit_code,
    main,
    run_daily_job,
)
from app.use_cases.errors import (
    ArticleAnalysisRequestError,
    ArticleSourceUnavailableError,
    SourceStructureChangedError,
)
from app.use_cases.process_daily_articles import (
    DailyArticleProcessor,
    SourceResult,
    count_outcomes,
)


def make_result(
    source: str,
    fetch_error: ArticleSourceUnavailableError | SourceStructureChangedError | None = None,
) -> SourceResult:
    return SourceResult(source, count_outcomes([]), fetch_error=fetch_error)


def test_build_fetchers_returns_all_target_sources_in_processing_order() -> None:
    fetchers = build_fetchers(create_autospec(httpx.Client))

    assert list(fetchers) == ["mod", "mhi", "khi", "subaru", "ihi", "melco", "nec", "hitachi"]


def test_decide_exit_code_succeeds_when_all_sources_were_processed() -> None:
    assert decide_exit_code([make_result("mod"), make_result("mhi")]) == EXIT_SUCCESS


def test_decide_exit_code_succeeds_when_source_is_temporarily_unavailable() -> None:
    results = [make_result("mod", ArticleSourceUnavailableError("mod", "503")), make_result("mhi")]

    assert decide_exit_code(results) == EXIT_SUCCESS


def test_decide_exit_code_fails_when_source_structure_changed() -> None:
    results = [make_result("mod"), make_result("mhi", SourceStructureChangedError("mhi", "変更"))]

    assert decide_exit_code(results) == EXIT_FAILURE


def make_processor(
    results: list[SourceResult] | None = None, error: Exception | None = None
) -> MagicMock:
    processor: MagicMock = create_autospec(DailyArticleProcessor, instance=True)
    processor.run.return_value = tuple(results or [])
    processor.run.side_effect = error
    return processor


def test_run_daily_job_returns_exit_code_decided_from_results() -> None:
    results = [make_result("mhi", SourceStructureChangedError("mhi", "変更"))]

    assert run_daily_job(make_processor(results)) == EXIT_FAILURE


def test_run_daily_job_logs_error_and_fails_when_processing_is_aborted(
    caplog: pytest.LogCaptureFixture,
) -> None:
    processor = make_processor(error=ArticleAnalysisRequestError("認証エラー"))

    assert run_daily_job(processor) == EXIT_FAILURE
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_main_fails_without_calling_processor_when_api_key_is_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    fake_run_daily_job = MagicMock()
    monkeypatch.setattr(daily_job, "run_daily_job", fake_run_daily_job)

    assert main() == EXIT_FAILURE
    fake_run_daily_job.assert_not_called()


def test_main_runs_daily_job_with_assembled_processor_and_returns_its_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(daily_job, "SessionLocal", MagicMock())
    fake_run_daily_job = MagicMock(return_value=EXIT_SUCCESS)
    monkeypatch.setattr(daily_job, "run_daily_job", fake_run_daily_job)

    assert main() == EXIT_SUCCESS
    (processor,) = fake_run_daily_job.call_args.args
    assert isinstance(processor, DailyArticleProcessor)
