from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.entities.category import Category


@dataclass
class Article:
    id: int | None
    source: str
    url: str
    title: str
    body: str
    published_at: datetime


@dataclass
class Summary:
    id: int | None
    article_id: int
    summary_text: str
    matched_categories: list[Category]
    mentions_price: bool
    mentions_israel: bool
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
