import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.use_cases.errors import ApplicationError, ExternalServiceError

logger = logging.getLogger(__name__)

# 応答の本文は固定の文言にする（DBのエラー内容などの内部情報を外に出さない。詳細はログで見る）
EXTERNAL_SERVICE_ERROR_DETAIL = "一時的に処理できません。時間をおいて再度お試しください"
INTERNAL_ERROR_DETAIL = "サーバー内部でエラーが発生しました"


def application_error_to_response(error: ApplicationError) -> JSONResponse:
    """`ApplicationError` をHTTPレスポンスに変換し、ログを出す。

    外部起因（`ExternalServiceError`）は503・WARN、それ以外（自分起因）は500・ERRORとする。
    """
    if isinstance(error, ExternalServiceError):
        logger.warning("外部サービスの障害でリクエストを処理できません: %s", error)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": EXTERNAL_SERVICE_ERROR_DETAIL},
        )
    logger.error("リクエストの処理中にエラーが発生しました: %s", error, exc_info=error)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": INTERNAL_ERROR_DETAIL},
    )


def register_error_handlers(app: FastAPI) -> None:
    """`ApplicationError`（とそのサブクラス）を捕捉する例外ハンドラーをアプリに登録する。"""

    @app.exception_handler(ApplicationError)
    async def handle_application_error(_request: Request, error: ApplicationError) -> JSONResponse:
        return application_error_to_response(error)
