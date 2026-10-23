from typing import Protocol

from app.entities.article import Article
from app.entities.article_analysis import ArticleAnalysis


class ArticleRepository(Protocol):
    """記事とその分析結果を永続化するポート。

    実装はinterface_adapters層のgatewayが担い、ユースケースにはこのProtocolを通じて注入する。
    """

    def exists_by_url(self, url: str) -> bool:
        """同じURLの記事が保存済みかを返す。保存済みの記事は再分析しない（料金対策）。

        Raises:
            ArticleStorageError: 保存先にアクセスできない場合。
        """
        ...

    def save_with_analysis(self, article: Article, analysis: ArticleAnalysis) -> None:
        """記事と分析結果（`Summary` に変換して保存）を1つのトランザクションで保存し、確定する。

        失敗した場合はどちらも保存しない。

        Raises:
            ArticleStorageError: 保存先にアクセスできない、または保存に失敗した場合。
        """
        ...
