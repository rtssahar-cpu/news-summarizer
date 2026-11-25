from datetime import UTC, date, datetime

from app.entities.category import Category
from app.interface_adapters.controllers.article_schemas import (
    SummarizedArticleListResponse,
    SummarizedArticleResponse,
)
from app.use_cases.article_summary_reader import SummarizedArticle
from app.use_cases.list_summarized_articles import JST

SUMMARIZED_ARTICLE = SummarizedArticle(
    article_id=1,
    source="mod",
    url="https://www.mod.go.jp/j/press/news/2026/11/18a.html",
    title="お知らせ",
    published_at=datetime(2026, 11, 18, tzinfo=JST),
    summary_text="概要: お知らせ。",
    matched_categories=(Category.STANDOFF_MISSILE, Category.CONTRACTOR_MITSUBISHI_HEAVY),
    mentions_price=True,
    mentions_israel=False,
    summarized_at=datetime(2026, 11, 17, 21, tzinfo=UTC),
)


def test_list_response_serializes_to_snake_case_json_with_date() -> None:
    response = SummarizedArticleListResponse(
        date=date(2026, 11, 18),
        articles=[SummarizedArticleResponse.from_summarized_article(SUMMARIZED_ARTICLE)],
    )

    assert response.model_dump(mode="json") == {
        "date": "2026-11-18",
        "articles": [
            {
                "article_id": 1,
                "source": "mod",
                "url": "https://www.mod.go.jp/j/press/news/2026/11/18a.html",
                "title": "お知らせ",
                "published_at": "2026-11-18T00:00:00+09:00",
                "summary_text": "概要: お知らせ。",
                "matched_categories": ["standoff_missile", "contractor_mitsubishi_heavy"],
                "mentions_price": True,
                "mentions_israel": False,
                "summarized_at": "2026-11-17T21:00:00Z",
            }
        ],
    }
