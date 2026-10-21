import dataclasses

import pytest

from app.entities.article_analysis import ArticleAnalysis
from app.entities.category import Category


def make_analysis(
    summary_text: str = "概要: 防衛装備庁と契約を締結",
    matched_categories: tuple[Category, ...] = (Category.STANDOFF_MISSILE,),
) -> ArticleAnalysis:
    return ArticleAnalysis(
        summary_text=summary_text,
        matched_categories=matched_categories,
        mentions_price=False,
        mentions_israel=False,
    )


def test_article_analysis_is_defense_related_when_any_category_matches() -> None:
    assert make_analysis().is_defense_related is True


def test_article_analysis_is_not_defense_related_without_categories() -> None:
    assert make_analysis(matched_categories=()).is_defense_related is False


def test_article_analysis_is_immutable() -> None:
    analysis = make_analysis()

    with pytest.raises(dataclasses.FrozenInstanceError):
        analysis.summary_text = "書き換え"  # type: ignore[misc]


@pytest.mark.parametrize("summary_text", ["", "  \n"])
def test_article_analysis_rejects_blank_summary(summary_text: str) -> None:
    with pytest.raises(ValueError, match="summary_text"):
        make_analysis(summary_text=summary_text)


def test_article_analysis_rejects_duplicate_categories() -> None:
    with pytest.raises(ValueError, match="duplicates"):
        make_analysis(matched_categories=(Category.CONTRACTOR_NEC, Category.CONTRACTOR_NEC))
