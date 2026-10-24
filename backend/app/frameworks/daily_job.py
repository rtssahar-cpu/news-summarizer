import logging
import os
import sys
from collections.abc import Iterable, Mapping

import httpx
from anthropic import Anthropic

from app.frameworks.database import SessionLocal
from app.interface_adapters.gateways.claude_article_analyzer import ClaudeArticleAnalyzer
from app.interface_adapters.gateways.hitachi_fetcher import HitachiNewsFetcher
from app.interface_adapters.gateways.hitachi_news_parser import SOURCE_NAME as HITACHI
from app.interface_adapters.gateways.ihi_fetcher import IhiNewsFetcher
from app.interface_adapters.gateways.ihi_news_parser import SOURCE_NAME as IHI
from app.interface_adapters.gateways.khi_fetcher import KhiPressReleaseFetcher
from app.interface_adapters.gateways.khi_news_parser import SOURCE_NAME as KHI
from app.interface_adapters.gateways.melco_fetcher import MelcoNewsFetcher
from app.interface_adapters.gateways.melco_news_parser import SOURCE_NAME as MELCO
from app.interface_adapters.gateways.mhi_fetcher import MhiPressReleaseFetcher
from app.interface_adapters.gateways.mhi_news_parser import SOURCE_NAME as MHI
from app.interface_adapters.gateways.mod_fetcher import ModPressReleaseFetcher
from app.interface_adapters.gateways.mod_rss_parser import SOURCE_NAME as MOD
from app.interface_adapters.gateways.nec_fetcher import NecPressReleaseFetcher
from app.interface_adapters.gateways.nec_news_parser import SOURCE_NAME as NEC
from app.interface_adapters.gateways.sqlalchemy_article_repository import (
    SqlAlchemyArticleRepository,
)
from app.interface_adapters.gateways.subaru_fetcher import SubaruNewsReleaseFetcher
from app.interface_adapters.gateways.subaru_news_parser import SOURCE_NAME as SUBARU
from app.use_cases.article_fetcher import ArticleFetcher
from app.use_cases.errors import InternalError
from app.use_cases.process_article import ArticleProcessor
from app.use_cases.process_daily_articles import DailyArticleProcessor, SourceResult

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
# 取得元サイトへのHTTPタイムアウト（秒）。PDFの取得もあるため、httpxの既定（5秒）より長くする
HTTP_TIMEOUT_SECONDS = 30.0
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

logger = logging.getLogger(__name__)


def build_fetchers(client: httpx.Client) -> Mapping[str, ArticleFetcher]:
    """日次処理の対象ソース（ソース名→fetcher）を、処理する順に返す。全fetcherで1つのclientを共有する。"""
    return {
        MOD: ModPressReleaseFetcher(client),
        MHI: MhiPressReleaseFetcher(client),
        KHI: KhiPressReleaseFetcher(client),
        SUBARU: SubaruNewsReleaseFetcher(client),
        IHI: IhiNewsFetcher(client),
        MELCO: MelcoNewsFetcher(client),
        NEC: NecPressReleaseFetcher(client),
        HITACHI: HitachiNewsFetcher(client),
    }


def decide_exit_code(results: Iterable[SourceResult]) -> int:
    """ソース別の結果から終了コードを決める。

    コードの修正が必要な失敗（ページ構造の変更等の `InternalError`）があれば失敗とし、
    通知の対象にする。
    一時的な取得失敗や分析の失敗は翌日に自然に回復するため、成功として扱う。
    """
    has_internal_error = any(isinstance(result.fetch_error, InternalError) for result in results)
    return EXIT_FAILURE if has_internal_error else EXIT_SUCCESS


def run_daily_job(processor: DailyArticleProcessor) -> int:
    """日次処理を実行し、終了コードを返す。

    処理全体を中断する例外（分析リクエストの失敗・DBの読み書きの失敗・想定外の例外）は、
    すべてコードや設定の修正が必要なものとしてERRORログに出し、失敗の終了コードを返す。
    """
    try:
        results = processor.run()
    except Exception:
        logger.exception("日次処理を中断しました")
        return EXIT_FAILURE

    exit_code = decide_exit_code(results)
    logger.info("日次処理が終了しました（終了コード %d）", exit_code)
    return exit_code


def main() -> int:
    """環境変数を読み込んで依存を組み立て、日次処理を実行する。外部への接続は終了時に閉じる。"""
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("環境変数 ANTHROPIC_API_KEY が設定されていません")
        return EXIT_FAILURE

    with (
        httpx.Client(timeout=HTTP_TIMEOUT_SECONDS) as http_client,
        Anthropic(api_key=api_key) as anthropic_client,
        SessionLocal() as session,
    ):
        processor = DailyArticleProcessor(
            build_fetchers(http_client),
            ArticleProcessor(
                ClaudeArticleAnalyzer(anthropic_client), SqlAlchemyArticleRepository(session)
            ),
        )
        return run_daily_job(processor)


if __name__ == "__main__":
    sys.exit(main())
