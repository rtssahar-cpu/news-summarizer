from datetime import UTC, datetime

from app.entities.article import Article, Summary
from app.entities.category import Category


def test_article_holds_fetched_fields() -> None:
    article = Article(
        id=1,
        source="mod",
        url="https://www.mod.go.jp/example",
        title="防衛省の発表",
        body="本文",
        published_at=datetime(2026, 10, 1, tzinfo=UTC),
    )

    assert article.source == "mod"
    assert article.url == "https://www.mod.go.jp/example"
    assert article.published_at == datetime(2026, 10, 1, tzinfo=UTC)


def test_summary_defaults_created_at_to_now_in_utc() -> None:
    before = datetime.now(UTC)

    summary = Summary(
        id=None,
        article_id=1,
        summary_text="要約",
        matched_categories=[Category.STANDOFF_MISSILE],
        mentions_price=True,
        mentions_israel=False,
    )

    after = datetime.now(UTC)

    assert before <= summary.created_at <= after
    assert summary.matched_categories == [Category.STANDOFF_MISSILE]
    assert summary.mentions_price is True
    assert summary.mentions_israel is False
