from typing import Protocol

from app.entities.article import Article


class ArticleFetcher(Protocol):
    """記事の取得元（防衛省・各社のプレスリリース等）から最新の記事を取得するポート。

    実装はinterface_adapters層のgatewayが担い、ユースケースにはこのProtocolを通じて注入する。
    """

    def fetch_recent_articles(self, limit: int = 5) -> list[Article]:
        """新しい順に最大 `limit` 件の記事を本文付きで返す。

        個別記事の取得に失敗した場合は、その記事をスキップして残りを返す。

        Raises:
            ArticleSourceUnavailableError: 取得元全体から記事を取得できない場合。
            SourceStructureChangedError: 取得元のページ構造が想定と異なる場合。
        """
        ...
