from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.entities.category import Category


@dataclass(frozen=True)
class SummarizedArticle:
    """一覧表示用の、要約済みの記事（記事と要約を合わせた読み出しモデル）。

    本文は長い（最大20万文字）ため含めない。全文は `url` の元記事で読む想定。
    """

    article_id: int
    source: str
    url: str
    title: str
    published_at: datetime
    summary_text: str
    matched_categories: tuple[Category, ...]
    mentions_price: bool
    mentions_israel: bool
    summarized_at: datetime


class ArticleSummaryReader(Protocol):
    """要約済みの記事を読み出すポート。

    実装はinterface_adapters層のgatewayが担い、ユースケースにはこのProtocolを通じて注入する。
    """

    def list_summarized_between(
        self, start: datetime, end: datetime
    ) -> tuple[SummarizedArticle, ...]:
        """`start` 以上 `end` 未満に要約された記事を、発表日の新しい順に返す。

        カテゴリに該当しない記事も含める（絞り込みは呼び出し側で行う）。

        Raises:
            ArticleStorageError: 保存先にアクセスできない場合。
        """
        ...
