import dataclasses
from datetime import UTC, datetime

import pytest

from app.entities.category import Category
from app.use_cases.article_summary_reader import SummarizedArticle

SUMMARIZED_ARTICLE = SummarizedArticle(
    article_id=1,
    source="mhi",
    url="https://www.mhi.com/jp/news/261016.html",
    title="防衛装備庁と契約を締結",
    published_at=datetime(2026, 10, 16, tzinfo=UTC),
    summary_text="概要: 防衛装備庁と契約を締結した。",
    matched_categories=(Category.CONTRACTOR_MITSUBISHI_HEAVY,),
    mentions_price=False,
    mentions_israel=False,
    summarized_at=datetime(2026, 10, 16, 21, tzinfo=UTC),
)


def test_summarized_article_is_immutable() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        SUMMARIZED_ARTICLE.title = "変更後のタイトル"  # type: ignore[misc]
