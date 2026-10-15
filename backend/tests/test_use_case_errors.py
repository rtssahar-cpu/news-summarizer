import pytest

from app.use_cases.errors import (
    ApplicationError,
    ArticleContentUnavailableError,
    ArticleSourceUnavailableError,
    ExternalServiceError,
    InternalError,
    SourceStructureChangedError,
)


def test_article_source_unavailable_error_holds_source_and_reason() -> None:
    error = ArticleSourceUnavailableError(source="mod", reason="HTTP 503")

    assert error.source == "mod"
    assert error.reason == "HTTP 503"
    assert str(error) == "記事ソース 'mod' から記事を取得できません: HTTP 503"


def test_article_source_unavailable_error_is_external_service_error() -> None:
    with pytest.raises(ExternalServiceError):
        raise ArticleSourceUnavailableError(source="mod", reason="timeout")


@pytest.mark.parametrize("error_category", [ExternalServiceError, InternalError])
def test_error_categories_can_be_caught_as_application_error(
    error_category: type[ApplicationError],
) -> None:
    with pytest.raises(ApplicationError):
        raise error_category("error")


def test_internal_error_is_not_external_service_error() -> None:
    assert not issubclass(InternalError, ExternalServiceError)


def test_source_structure_changed_error_holds_source_and_reason() -> None:
    error = SourceStructureChangedError(source="mod", reason="一覧が空")

    assert error.source == "mod"
    assert error.reason == "一覧が空"
    assert str(error) == "記事ソース 'mod' のページ構造が想定と異なります: 一覧が空"


@pytest.mark.parametrize(
    ("error_class", "category"),
    [
        (ArticleSourceUnavailableError, ExternalServiceError),
        (ArticleContentUnavailableError, ExternalServiceError),
        (SourceStructureChangedError, InternalError),
    ],
)
def test_concrete_errors_belong_to_expected_category(
    error_class: type[ApplicationError], category: type[ApplicationError]
) -> None:
    assert issubclass(error_class, category)
