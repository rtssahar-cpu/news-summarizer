import os
from collections.abc import Generator

from fastapi import FastAPI

from app.frameworks.database import SessionLocal
from app.interface_adapters.controllers.articles_controller import (
    ListerProvider,
    build_articles_router,
)
from app.interface_adapters.controllers.error_handlers import register_error_handlers
from app.interface_adapters.controllers.health_controller import build_health_router
from app.interface_adapters.gateways.sqlalchemy_article_summary_reader import (
    SqlAlchemyArticleSummaryReader,
)
from app.use_cases.list_summarized_articles import SummarizedArticleLister


def provide_summarized_article_lister() -> Generator[SummarizedArticleLister, None, None]:
    """リクエストごとにSessionを開いてユースケースを組み立て、応答の後にSessionを閉じる。"""
    with SessionLocal() as session:
        yield SummarizedArticleLister(SqlAlchemyArticleSummaryReader(session))


def create_app(app_version: str, provide_lister: ListerProvider) -> FastAPI:
    """アプリを組み立てる。DBに依存する部分（`provide_lister`）はテストで差し替えられるよう注入する。"""
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(build_health_router(app_version))
    app.include_router(build_articles_router(provide_lister))
    return app


# APP_VERSION はビルド時にコミット SHA が埋め込まれる（Dockerfile の production ステージ）
app = create_app(
    app_version=os.environ.get("APP_VERSION", "unknown"),
    provide_lister=provide_summarized_article_lister,
)
