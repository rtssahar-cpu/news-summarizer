from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.entities.category import Category
from app.use_cases.article_summary_reader import SummarizedArticle


class SummarizedArticleResponse(BaseModel):
    """一覧APIで返す記事1件分のJSON。本文は返さない（全文は `url` の元記事で読む）。"""

    model_config = ConfigDict(frozen=True)

    article_id: int
    source: str
    url: str
    title: str
    published_at: datetime
    summary_text: str
    matched_categories: list[Category]
    mentions_price: bool
    mentions_israel: bool
    summarized_at: datetime

    @classmethod
    def from_summarized_article(cls, article: SummarizedArticle) -> "SummarizedArticleResponse":
        return cls(
            article_id=article.article_id,
            source=article.source,
            url=article.url,
            title=article.title,
            published_at=article.published_at,
            summary_text=article.summary_text,
            matched_categories=list(article.matched_categories),
            mentions_price=article.mentions_price,
            mentions_israel=article.mentions_israel,
            summarized_at=article.summarized_at,
        )


class SummarizedArticleListResponse(BaseModel):
    """`GET /articles` の応答。どの日（JST）の一覧かを `date` で返す。"""

    model_config = ConfigDict(frozen=True)

    date: date
    articles: list[SummarizedArticleResponse]
