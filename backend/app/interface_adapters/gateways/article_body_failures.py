from collections.abc import Sequence

import httpx

from app.use_cases.errors import (
    ArticleContentUnavailableError,
    ArticleSourceUnavailableError,
    SourceStructureChangedError,
)

# fetcherが記事をスキップする原因となる、個別記事の本文の取得・抽出の失敗
type ArticleBodyFailure = httpx.HTTPError | ArticleContentUnavailableError


def is_transient_body_failure(failure: ArticleBodyFailure) -> bool:
    """時間をおけば回復し得る失敗（通信エラー・429・5xx）かを返す。

    3xx・4xxや本文の抽出失敗は、URLやページ構造の変更が疑われるため一時的とみなさない。
    """
    if isinstance(failure, httpx.TransportError):
        return True
    if isinstance(failure, httpx.HTTPStatusError):
        status_code = failure.response.status_code
        return status_code == httpx.codes.TOO_MANY_REQUESTS or httpx.codes.is_server_error(
            status_code
        )
    return False


def build_all_bodies_failed_error(
    source: str, failures: Sequence[ArticleBodyFailure]
) -> ArticleSourceUnavailableError | SourceStructureChangedError:
    """試した記事の本文がすべて取得・抽出できなかった場合に、fetcherが送出する例外を返す。

    失敗がすべて一時的なものならソース全体の一時的な取得失敗とし、
    1件でもそれ以外を含めば、記事URLやページ構造の変更としてコードの修正を促す。
    `failures` は1件以上であること。
    """
    reason = (
        f"試した{len(failures)}件の記事本文をすべて取得・抽出できません"
        f"（最初の失敗: {failures[0]}）"
    )
    if all(is_transient_body_failure(failure) for failure in failures):
        return ArticleSourceUnavailableError(source=source, reason=reason)
    return SourceStructureChangedError(source=source, reason=reason)
