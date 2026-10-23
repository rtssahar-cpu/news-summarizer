import logging
from enum import StrEnum

from app.entities.article import Article
from app.use_cases.article_analyzer import ArticleAnalyzer
from app.use_cases.article_repository import ArticleRepository
from app.use_cases.errors import ArticleAnalysisUnavailableError

logger = logging.getLogger(__name__)


class ArticleOutcome(StrEnum):
    """記事1件を処理した結果。日次処理でソース別の件数を集計するために使う。"""

    SAVED = "saved"
    ALREADY_STORED = "already_stored"
    ANALYSIS_FAILED = "analysis_failed"


class ArticleProcessor:
    """記事1件について、保存済みかを確認し、未保存なら分析してDBに保存する。"""

    def __init__(self, analyzer: ArticleAnalyzer, repository: ArticleRepository) -> None:
        self._analyzer = analyzer
        self._repository = repository

    def process(self, article: Article) -> ArticleOutcome:
        """記事を処理した結果を返す。

        保存済みの記事は分析しない（料金対策）。分析できなかった記事は保存せず、翌日に再挑戦させる。

        Raises:
            ArticleAnalysisRequestError: 分析サービスがリクエスト自体を受け付けない場合。
            ArticleStorageError: 保存先の読み書きに失敗した場合。
        """
        if self._repository.exists_by_url(article.url):
            return ArticleOutcome.ALREADY_STORED

        try:
            analysis = self._analyzer.analyze(article)
        except ArticleAnalysisUnavailableError as error:
            logger.warning("記事を分析できないためスキップ: %s", error)
            return ArticleOutcome.ANALYSIS_FAILED

        self._repository.save_with_analysis(article, analysis)
        return ArticleOutcome.SAVED
