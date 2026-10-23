from datetime import UTC, datetime
from unittest.mock import MagicMock, create_autospec

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.entities.article import Article
from app.entities.article_analysis import ArticleAnalysis
from app.entities.category import Category
from app.interface_adapters.gateways.models import ArticleModel
from app.interface_adapters.gateways.sqlalchemy_article_repository import (
    SqlAlchemyArticleRepository,
)
from app.use_cases.errors import ArticleStorageError

ARTICLE = Article(
    id=None,
    source="mhi",
    url="https://www.mhi.com/jp/news/261016.html",
    title="防衛装備庁と契約を締結",
    body="三菱重工業は、防衛装備庁と契約を締結した。",
    published_at=datetime(2026, 10, 16, tzinfo=UTC),
)
ANALYSIS = ArticleAnalysis(
    summary_text="概要: 防衛装備庁と契約を締結した。",
    matched_categories=(Category.CONTRACTOR_MITSUBISHI_HEAVY, Category.STANDOFF_MISSILE),
    mentions_price=True,
    mentions_israel=False,
)


def make_session() -> MagicMock:
    session: MagicMock = create_autospec(Session, instance=True)
    return session


def test_exists_by_url_returns_true_when_article_is_stored() -> None:
    session = make_session()
    session.scalar.return_value = True

    assert SqlAlchemyArticleRepository(session).exists_by_url(ARTICLE.url) is True


def test_exists_by_url_returns_false_when_article_is_not_stored() -> None:
    session = make_session()
    session.scalar.return_value = False

    assert SqlAlchemyArticleRepository(session).exists_by_url(ARTICLE.url) is False


def test_exists_by_url_converts_database_error_to_storage_error() -> None:
    session = make_session()
    error = OperationalError("SELECT", {}, Exception("connection refused"))
    session.scalar.side_effect = error

    with pytest.raises(ArticleStorageError) as exc_info:
        SqlAlchemyArticleRepository(session).exists_by_url(ARTICLE.url)

    assert exc_info.value.__cause__ is error


def test_save_with_analysis_adds_article_with_summary_and_commits() -> None:
    session = make_session()

    SqlAlchemyArticleRepository(session).save_with_analysis(ARTICLE, ANALYSIS)

    saved: ArticleModel = session.add.call_args.args[0]
    assert (saved.source, saved.url, saved.title) == ("mhi", ARTICLE.url, ARTICLE.title)
    assert saved.published_at == ARTICLE.published_at
    assert saved.summary is not None
    assert saved.summary.summary_text == ANALYSIS.summary_text
    assert saved.summary.matched_categories == ["contractor_mitsubishi_heavy", "standoff_missile"]
    assert (saved.summary.mentions_price, saved.summary.mentions_israel) == (True, False)
    assert saved.summary.created_at.tzinfo is UTC
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


def test_save_with_analysis_rolls_back_and_converts_database_error() -> None:
    session = make_session()
    error = IntegrityError("INSERT", {}, Exception("duplicate key"))
    session.commit.side_effect = error

    with pytest.raises(ArticleStorageError) as exc_info:
        SqlAlchemyArticleRepository(session).save_with_analysis(ARTICLE, ANALYSIS)

    assert exc_info.value.__cause__ is error
    session.rollback.assert_called_once_with()
