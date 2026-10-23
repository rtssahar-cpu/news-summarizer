import pytest

from app.use_cases.errors import (
    ApplicationError,
    ArticleAnalysisRequestError,
    ArticleAnalysisUnavailableError,
    ArticleContentUnavailableError,
    ArticleSourceUnavailableError,
    ArticleStorageError,
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


def test_article_analysis_unavailable_error_holds_article_url_and_reason() -> None:
    error = ArticleAnalysisUnavailableError(
        article_url="https://example.com/news/1", reason="応答が拒否された"
    )

    assert error.article_url == "https://example.com/news/1"
    assert error.reason == "応答が拒否された"
    assert str(error) == "記事 'https://example.com/news/1' を分析できません: 応答が拒否された"


def test_article_analysis_request_error_holds_reason() -> None:
    error = ArticleAnalysisRequestError(reason="認証エラー")

    assert error.reason == "認証エラー"
    assert str(error) == "分析サービスがリクエストを受け付けません: 認証エラー"


def test_article_storage_error_holds_reason() -> None:
    error = ArticleStorageError(reason="接続できない")

    assert error.reason == "接続できない"
    assert str(error) == "記事の保存先の読み書きに失敗しました: 接続できない"


@pytest.mark.parametrize(
    ("error_class", "category"),
    [
        (ArticleSourceUnavailableError, ExternalServiceError),
        (ArticleContentUnavailableError, ExternalServiceError),
        (ArticleAnalysisUnavailableError, ExternalServiceError),
        (ArticleAnalysisRequestError, InternalError),
        (SourceStructureChangedError, InternalError),
        (ArticleStorageError, InternalError),
    ],
)
def test_concrete_errors_belong_to_expected_category(
    error_class: type[ApplicationError], category: type[ApplicationError]
) -> None:
    assert issubclass(error_class, category)
