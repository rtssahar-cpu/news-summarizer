import pytest

from app.entities.category import CATEGORY_CRITERIA, Category


def test_category_members_have_unique_string_values() -> None:
    values = [member.value for member in Category]

    assert len(values) == len(set(values))


def test_category_member_value_matches_expected_code() -> None:
    assert Category.UNMANNED_UUV.value == "unmanned_uuv"
    assert Category.THREE_DOCUMENTS.value == "three_documents"


def test_every_category_has_non_blank_criterion() -> None:
    assert set(CATEGORY_CRITERIA) == set(Category)
    assert all(criterion.strip() for criterion in CATEGORY_CRITERIA.values())


def test_contractor_criterion_names_the_company() -> None:
    assert "日立製作所" in CATEGORY_CRITERIA[Category.CONTRACTOR_HITACHI]
    assert "SUBARU" in CATEGORY_CRITERIA[Category.CONTRACTOR_SUBARU]


def test_category_criteria_is_read_only() -> None:
    with pytest.raises(TypeError):
        CATEGORY_CRITERIA[Category.UNMANNED_UUV] = "変更"  # type: ignore[index]
