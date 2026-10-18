import pytest

from app.interface_adapters.gateways.ihi_article_parser import extract_ihi_article_body
from app.use_cases.errors import ArticleContentUnavailableError


def build_article(subtitle: str, body: str) -> str:
    return f"""
<div class="m-entry-detail">
  <header class="m-entry-detail_title">
    <div class="m-entry-detail_items"><time>2026年10月07日</time><span>プレスリリース</span></div>
    <div class="m-entry-detail_category"><span>産業システム・汎用機械</span></div>
    <h1>「LH₂ BOG圧縮機」が採用<div class="size-xsmall">{subtitle}</div></h1>
  </header>
  <p class="m-en-link"><a href="/en/all_news/">English page</a></p>
  {body}
  <p class="m-entry-detail_back m-btn"><a href="/all_news/">ニューストップへ</a></p>
</div>
"""


ARTICLE_BODY = """
<p>LH₂ BOG圧縮機が、このたび採用されました。<br>
世界初の商用規模の液化水素基地です。</p>
<h4>主な特長</h4>
<dl class="m-dl">
  <dt><span>・</span>真空ジャケット</dt>
  <dd>熱の侵入を抑制します。</dd>
</dl>
<table><tbody><tr><td>（1）所在地</td><td>東京都江東区</td></tr></tbody></table>
"""


def test_extract_ihi_article_body_puts_subtitle_first_and_excludes_non_body() -> None:
    body = extract_ihi_article_body(build_article("～安定操業に貢献～", ARTICLE_BODY))

    assert body == (
        "～安定操業に貢献～\n"
        "LH₂ BOG圧縮機が、このたび採用されました。\n"
        "世界初の商用規模の液化水素基地です。\n"
        "主な特長\n"
        "・真空ジャケット\n"
        "熱の侵入を抑制します。\n"
        "（1）所在地\n"
        "東京都江東区"
    )


def test_extract_ihi_article_body_without_subtitle() -> None:
    body = extract_ihi_article_body(build_article("", "<p>本文です。</p>"))

    assert body == "本文です。"


def test_extract_ihi_article_body_raises_when_detail_area_missing() -> None:
    with pytest.raises(ArticleContentUnavailableError, match="本文の領域が見つかりません"):
        extract_ihi_article_body("<html><body><p>本文</p></body></html>")


def test_extract_ihi_article_body_raises_when_body_is_empty() -> None:
    with pytest.raises(ArticleContentUnavailableError, match="本文が空です"):
        extract_ihi_article_body(build_article("～副題のみ～", ""))
