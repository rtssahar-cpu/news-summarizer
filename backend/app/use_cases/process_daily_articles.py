import logging
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass

from app.use_cases.article_fetcher import ArticleFetcher
from app.use_cases.errors import ArticleSourceUnavailableError, SourceStructureChangedError
from app.use_cases.process_article import ArticleOutcome, ArticleProcessor

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SourceResult:
    """1つのソースを処理した結果。記事の処理結果ごとの件数と、ソース単位で中断した場合はその原因を持つ。"""

    source: str
    outcome_counts: Mapping[ArticleOutcome, int]
    fetch_error: ArticleSourceUnavailableError | SourceStructureChangedError | None = None


class DailyArticleProcessor:
    """各ソースから最新の記事を取得し、1件ずつ処理してソース別の件数を集計する。"""

    def __init__(
        self,
        fetchers: Mapping[str, ArticleFetcher],
        processor: ArticleProcessor,
        articles_per_source: int = 5,
    ) -> None:
        self._fetchers = fetchers
        self._processor = processor
        self._articles_per_source = articles_per_source

    def run(self) -> tuple[SourceResult, ...]:
        """ソースごとに順番に処理し、ソース別の結果を返す。

        取得に失敗したソースだけを中断し、他のソースは続ける。

        Raises:
            ArticleAnalysisRequestError: 分析サービスがリクエスト自体を受け付けない場合。
            ArticleStorageError: 保存先の読み書きに失敗した場合。
        """
        return tuple(
            self._process_source(source, fetcher) for source, fetcher in self._fetchers.items()
        )

    def _process_source(self, source: str, fetcher: ArticleFetcher) -> SourceResult:
        try:
            articles = fetcher.fetch_recent_articles(self._articles_per_source)
        except ArticleSourceUnavailableError as error:
            logger.warning("ソースから記事を取得できないため中断: %s", error)
            return SourceResult(source, count_outcomes([]), fetch_error=error)
        except SourceStructureChangedError as error:
            logger.error("ソースのページ構造が想定と異なるため中断: %s", error)
            return SourceResult(source, count_outcomes([]), fetch_error=error)

        outcome_counts = count_outcomes([self._processor.process(article) for article in articles])
        summary = ", ".join(f"{outcome}={count}" for outcome, count in outcome_counts.items())
        logger.info("ソース '%s' の処理結果: %s", source, summary)
        return SourceResult(source, outcome_counts)


def count_outcomes(outcomes: list[ArticleOutcome]) -> Mapping[ArticleOutcome, int]:
    """処理結果ごとの件数を返す。1件もない処理結果も0件として含める。"""
    counter = Counter(outcomes)
    return {outcome: counter[outcome] for outcome in ArticleOutcome}
