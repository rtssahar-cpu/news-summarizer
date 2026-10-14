from app.interface_adapters.gateways.models import ArticleModel, SummaryModel


def test_article_model_table_name_and_key_columns() -> None:
    columns = ArticleModel.__table__.columns

    assert ArticleModel.__tablename__ == "articles"
    assert columns["id"].primary_key is True
    assert columns["url"].unique is True


def test_summary_model_table_name_and_foreign_key() -> None:
    columns = SummaryModel.__table__.columns
    foreign_key = next(iter(columns["article_id"].foreign_keys))

    assert SummaryModel.__tablename__ == "summaries"
    assert columns["article_id"].unique is True
    assert foreign_key.column.table.name == "articles"


def test_summary_model_classification_columns_are_required() -> None:
    columns = SummaryModel.__table__.columns

    assert columns["matched_categories"].nullable is False
    assert columns["mentions_price"].nullable is False
    assert columns["mentions_israel"].nullable is False
