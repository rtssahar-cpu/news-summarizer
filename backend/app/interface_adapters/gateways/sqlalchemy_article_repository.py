from datetime import UTC, datetime

from sqlalchemy import exists, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.entities.article import Article
from app.entities.article_analysis import ArticleAnalysis
from app.interface_adapters.gateways.models import ArticleModel, SummaryModel
from app.use_cases.errors import ArticleStorageError


class SqlAlchemyArticleRepository:
    """SQLAlchemyのSessionを使って記事と分析結果をDBに保存する `ArticleRepository` の実装。

    Sessionの生成・破棄は呼び出し元（frameworks層）が担い、このクラスには注入する。
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def exists_by_url(self, url: str) -> bool:
        statement = select(exists().where(ArticleModel.url == url))
        try:
            return bool(self._session.scalar(statement))
        except SQLAlchemyError as error:
            raise ArticleStorageError(f"保存済みかを確認できません: {url}") from error

    def save_with_analysis(self, article: Article, analysis: ArticleAnalysis) -> None:
        article_model = ArticleModel(
            source=article.source,
            url=article.url,
            title=article.title,
            body=article.body,
            published_at=article.published_at,
        )
        # relationship経由で紐付けるため、記事のidが採番される前でもSummaryを組み立てられる
        article_model.summary = SummaryModel(
            summary_text=analysis.summary_text,
            matched_categories=[category.value for category in analysis.matched_categories],
            mentions_price=analysis.mentions_price,
            mentions_israel=analysis.mentions_israel,
            created_at=datetime.now(UTC),
        )
        try:
            self._session.add(article_model)
            self._session.commit()
        except SQLAlchemyError as error:
            self._session.rollback()
            raise ArticleStorageError(f"記事を保存できません: {article.url}") from error
