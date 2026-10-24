from collections.abc import Iterable, Mapping

import httpx

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
from app.interface_adapters.gateways.subaru_fetcher import SubaruNewsReleaseFetcher
from app.interface_adapters.gateways.subaru_news_parser import SOURCE_NAME as SUBARU
from app.use_cases.article_fetcher import ArticleFetcher
from app.use_cases.errors import InternalError
from app.use_cases.process_daily_articles import SourceResult

EXIT_SUCCESS = 0
EXIT_FAILURE = 1


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
