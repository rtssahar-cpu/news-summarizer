import httpx
import pytest

from app.interface_adapters.gateways.article_body_failures import (
    ArticleBodyFailure,
    build_all_bodies_failed_error,
    is_transient_body_failure,
)
from app.use_cases.errors import (
    ArticleContentUnavailableError,
    ArticleSourceUnavailableError,
    SourceStructureChangedError,
)

REQUEST = httpx.Request("GET", "https://example.com/news/1")


def status_error(status_code: int) -> httpx.HTTPStatusError:
    return httpx.HTTPStatusError(
        f"status {status_code}", request=REQUEST, response=httpx.Response(status_code)
    )


@pytest.mark.parametrize(
    "failure",
    [
        httpx.ConnectTimeout("timeout", request=REQUEST),
        httpx.ConnectError("refused", request=REQUEST),
        status_error(429),
        status_error(503),
    ],
    ids=["timeout", "connect_error", "429", "503"],
)
def test_is_transient_body_failure_returns_true_for_recoverable_failures(
    failure: ArticleBodyFailure,
) -> None:
    assert is_transient_body_failure(failure)


@pytest.mark.parametrize(
    "failure",
    [
        status_error(301),
        status_error(404),
        ArticleContentUnavailableError("本文の領域が見つかりません"),
    ],
    ids=["301", "404", "content_unavailable"],
)
def test_is_transient_body_failure_returns_false_for_other_failures(
    failure: ArticleBodyFailure,
) -> None:
    assert not is_transient_body_failure(failure)


def test_build_all_bodies_failed_error_returns_source_unavailable_when_all_transient() -> None:
    error = build_all_bodies_failed_error(
        "subaru", [status_error(503), httpx.ReadTimeout("timeout", request=REQUEST)]
    )

    assert isinstance(error, ArticleSourceUnavailableError)
    assert error.source == "subaru"
    assert "試した2件の記事本文をすべて取得・抽出できません" in error.reason
    assert "status 503" in error.reason


@pytest.mark.parametrize(
    "failures",
    [
        [status_error(301), status_error(301)],
        [status_error(503), ArticleContentUnavailableError("本文が空です")],
    ],
    ids=["all_redirect", "mixed"],
)
def test_build_all_bodies_failed_error_returns_structure_changed_otherwise(
    failures: list[ArticleBodyFailure],
) -> None:
    error = build_all_bodies_failed_error("subaru", failures)

    assert isinstance(error, SourceStructureChangedError)
    assert error.source == "subaru"
