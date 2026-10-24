from unittest.mock import create_autospec

import httpx

from app.frameworks.daily_job import EXIT_FAILURE, EXIT_SUCCESS, build_fetchers, decide_exit_code
from app.use_cases.errors import ArticleSourceUnavailableError, SourceStructureChangedError
from app.use_cases.process_daily_articles import SourceResult, count_outcomes


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
