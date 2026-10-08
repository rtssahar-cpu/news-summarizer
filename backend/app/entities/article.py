from dataclasses import dataclass
from datetime import datetime


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
    created_at: datetime
