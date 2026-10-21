from typing import Protocol

from app.entities.article import Article
from app.entities.article_analysis import ArticleAnalysis


class ArticleAnalyzer(Protocol):
    """記事をAIで分析し、要約・該当カテゴリ・横断的なフラグを判定するポート。

    実装はinterface_adapters層のgatewayが担い、ユースケースにはこのProtocolを通じて注入する。
    """

    def analyze(self, article: Article) -> ArticleAnalysis:
        """1記事を分析した結果を返す。防衛と無関係な記事もカテゴリ0件として要約を返す。

        Raises:
            ArticleAnalysisUnavailableError: その記事を分析できない場合（APIの一時的な障害、
                応答の拒否・出力上限への到達、本文が長すぎる等）。呼び出し元は記事をスキップする。
            ArticleAnalysisRequestError: 分析サービスがリクエスト自体を受け付けない場合
                （認証エラー、不正なリクエスト等）。設定やコードの修正が必要。
        """
        ...
