from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, contains_eager

from app.entities.category import Category
from app.interface_adapters.gateways.models import ArticleModel, SummaryModel
from app.use_cases.article_summary_reader import SummarizedArticle
from app.use_cases.errors import ArticleStorageError


class SqlAlchemyArticleSummaryReader:
    """SQLAlchemyのSessionを使って要約済みの記事をDBから読み出す `ArticleSummaryReader` の実装。

    Sessionの生成・破棄は呼び出し元（frameworks層）が担い、このクラスには注入する。
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_summarized_between(
        self, start: datetime, end: datetime
    ) -> tuple[SummarizedArticle, ...]:
        # 記事と要約を1回のクエリで読み出す（記事ごとに追加のクエリを発行しないため）
        statement = (
            select(SummaryModel)
            .join(SummaryModel.article)
            .options(contains_eager(SummaryModel.article))
            .where(SummaryModel.created_at >= start, SummaryModel.created_at < end)
            .order_by(ArticleModel.published_at.desc(), ArticleModel.id.desc())
        )
        try:
            summaries = self._session.scalars(statement).all()
        except SQLAlchemyError as error:
            raise ArticleStorageError(
                f"要約済みの記事を読み出せません: {start.isoformat()} - {end.isoformat()}"
            ) from error
        return tuple(to_summarized_article(summary) for summary in summaries)


def to_summarized_article(summary: SummaryModel) -> SummarizedArticle:
    """ORMモデルの要約（記事を紐付け済み）を一覧表示用の読み出しモデルに変換する。"""
    article = summary.article
    return SummarizedArticle(
        article_id=article.id,
        source=article.source,
        url=article.url,
        title=article.title,
        published_at=article.published_at,
        summary_text=summary.summary_text,
        matched_categories=tuple(Category(value) for value in summary.matched_categories),
        mentions_price=summary.mentions_price,
        mentions_israel=summary.mentions_israel,
        summarized_at=summary.created_at,
    )
