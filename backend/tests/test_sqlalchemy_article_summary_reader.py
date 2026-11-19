from datetime import UTC, datetime
from unittest.mock import MagicMock, create_autospec

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.entities.category import Category
from app.interface_adapters.gateways.models import ArticleModel, SummaryModel
from app.interface_adapters.gateways.sqlalchemy_article_summary_reader import (
    SqlAlchemyArticleSummaryReader,
)
from app.use_cases.article_summary_reader import SummarizedArticle
from app.use_cases.errors import ArticleStorageError

START = datetime(2026, 11, 17, 15, tzinfo=UTC)
END = datetime(2026, 11, 18, 15, tzinfo=UTC)
PUBLISHED_AT = datetime(2026, 11, 16, tzinfo=UTC)
SUMMARIZED_AT = datetime(2026, 11, 17, 21, tzinfo=UTC)


def make_summary_model() -> SummaryModel:
    article = ArticleModel(
        id=1,
        source="mhi",
        url="https://www.mhi.com/jp/news/261116.html",
        title="防衛装備庁と契約を締結",
        body="三菱重工業は、防衛装備庁と契約を締結した。",
        published_at=PUBLISHED_AT,
    )
    return SummaryModel(
        id=10,
        article=article,
        summary_text="概要: 防衛装備庁と契約を締結した。",
        matched_categories=[Category.CONTRACTOR_MITSUBISHI_HEAVY.value],
        mentions_price=True,
        mentions_israel=False,
        created_at=SUMMARIZED_AT,
    )


def make_session() -> MagicMock:
    session: MagicMock = create_autospec(Session, instance=True)
    return session


def test_list_summarized_between_converts_models_to_summarized_articles() -> None:
    session = make_session()
    session.scalars.return_value.all.return_value = [make_summary_model()]

    result = SqlAlchemyArticleSummaryReader(session).list_summarized_between(START, END)

    assert result == (
        SummarizedArticle(
            article_id=1,
            source="mhi",
            url="https://www.mhi.com/jp/news/261116.html",
            title="防衛装備庁と契約を締結",
            published_at=PUBLISHED_AT,
            summary_text="概要: 防衛装備庁と契約を締結した。",
            matched_categories=(Category.CONTRACTOR_MITSUBISHI_HEAVY,),
            mentions_price=True,
            mentions_israel=False,
            summarized_at=SUMMARIZED_AT,
        ),
    )


def test_list_summarized_between_returns_empty_tuple_when_nothing_summarized() -> None:
    session = make_session()
    session.scalars.return_value.all.return_value = []

    assert SqlAlchemyArticleSummaryReader(session).list_summarized_between(START, END) == ()


def test_list_summarized_between_converts_database_error_to_storage_error() -> None:
    session = make_session()
    error = OperationalError("SELECT", {}, Exception("connection refused"))
    session.scalars.side_effect = error

    with pytest.raises(ArticleStorageError) as exc_info:
        SqlAlchemyArticleSummaryReader(session).list_summarized_between(START, END)

    assert exc_info.value.__cause__ is error
