import pytest
from pydantic import ValidationError

from app.entities.category import Category
from app.interface_adapters.gateways.article_analysis_output import ArticleAnalysisOutput


def make_output(summary_text: str, matched_categories: list[Category]) -> ArticleAnalysisOutput:
    return ArticleAnalysisOutput(
        summary_text=summary_text,
        matched_categories=matched_categories,
        mentions_price=True,
        mentions_israel=False,
    )


def test_to_entity_converts_all_fields() -> None:
    output = make_output(" 概要: 契約を締結した。\n", [Category.STANDOFF_MISSILE])

    analysis = output.to_entity()

    assert analysis.summary_text == "概要: 契約を締結した。"
    assert analysis.matched_categories == (Category.STANDOFF_MISSILE,)
    assert analysis.mentions_price is True
    assert analysis.mentions_israel is False


def test_to_entity_removes_duplicate_categories_keeping_order() -> None:
    output = make_output(
        "概要: 契約を締結した。",
        [Category.CONTRACTOR_NEC, Category.ELECTRONIC_WARFARE, Category.CONTRACTOR_NEC],
    )

    assert output.to_entity().matched_categories == (
        Category.CONTRACTOR_NEC,
        Category.ELECTRONIC_WARFARE,
    )


def test_to_entity_rejects_blank_summary() -> None:
    with pytest.raises(ValueError, match="summary_text"):
        make_output("  \n", []).to_entity()


def test_unknown_category_code_is_rejected_by_validation() -> None:
    with pytest.raises(ValidationError):
        ArticleAnalysisOutput.model_validate(
            {
                "summary_text": "概要: 契約を締結した。",
                "matched_categories": ["unknown_category"],
                "mentions_price": False,
                "mentions_israel": False,
            }
        )


def test_json_schema_restricts_categories_to_known_codes() -> None:
    schema = ArticleAnalysisOutput.model_json_schema()

    assert set(schema["$defs"]["Category"]["enum"]) == {category.value for category in Category}
