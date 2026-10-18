import httpx

from app.interface_adapters.gateways.mod_fetcher import ModPressReleaseFetcher
from app.use_cases.article_fetcher import ArticleFetcher


def test_mod_press_release_fetcher_satisfies_article_fetcher_protocol() -> None:
    # 型注釈付きの代入により、Protocolへの適合をmypyで検査する
    with httpx.Client() as client:
        fetcher: ArticleFetcher = ModPressReleaseFetcher(client)

    assert callable(fetcher.fetch_recent_articles)
