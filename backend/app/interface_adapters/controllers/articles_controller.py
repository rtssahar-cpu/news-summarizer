from collections.abc import Callable, Iterator
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.interface_adapters.controllers.article_schemas import (
    SummarizedArticleListResponse,
    SummarizedArticleResponse,
)
from app.use_cases.list_summarized_articles import SummarizedArticleLister

# リクエストごとにユースケースを渡す関数（FastAPIの依存関数）。
# yield の後でDBのSessionを閉じられるよう、ジェネレーターにしている
ListerProvider = Callable[[], Iterator[SummarizedArticleLister]]


def build_articles_router(provide_lister: ListerProvider) -> APIRouter:
    router = APIRouter()

    @router.get("/articles", response_model=SummarizedArticleListResponse)
    def list_summarized_articles(
        lister: Annotated[SummarizedArticleLister, Depends(provide_lister)],
        requested_day: Annotated[date | None, Query(alias="date")] = None,
    ) -> SummarizedArticleListResponse:
        """`date`（JST、YYYY-MM-DD）に要約した記事の一覧を返す。省略時は今日（JST）。"""
        target_day = requested_day if requested_day is not None else lister.today()
        articles = lister.list_for(target_day)
        return SummarizedArticleListResponse(
            date=target_day,
            articles=[SummarizedArticleResponse.from_summarized_article(a) for a in articles],
        )

    return router
