from app.entities.category import Category


def test_category_members_have_unique_string_values() -> None:
    values = [member.value for member in Category]

    assert len(values) == len(set(values))


def test_category_member_value_matches_expected_code() -> None:
    assert Category.UNMANNED_UUV.value == "unmanned_uuv"
    assert Category.THREE_DOCUMENTS.value == "three_documents"
