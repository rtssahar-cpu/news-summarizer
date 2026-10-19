import pytest

from app.interface_adapters.gateways.nec_article_parser import extract_nec_article_body
from app.use_cases.errors import ArticleContentUnavailableError


def build_article(subtitle: str, body: str) -> str:
    return f"""
<div class="str-pageTitle"><div class="inner">
  <h1 class="hdg">NEC、VLM技術を開発</h1>{subtitle}
</div></div>
<div class="ls-row str-column-main">
  {body}
  <div class="comp-sns"><ul class="list"><li><a href="https://twitter.com/share">Tweet</a></li></ul></div>
  <div class="mod-box mt-70"><div class="inner"><p>NECは、安全・安心・公平・効率という<br>
  社会価値を創造し、</p></div></div>
</div>
"""


ARTICLE_BODY = """
<div class="str-outer"><div class="str-inner">
  <p class=" align-right">2026年10月14日<br>日本電気株式会社</p>
</div></div>
<div class="str-outer"><div class="str-inner">
  <h3 class="mod-hdg-l3-02"><span>背景</span></h3>
</div></div>
<div class="str-outer"><div class="str-inner">
  <p class=" align-left">NECは、<span>2026</span>年に技術を開発しました(注1)。</p>
</div></div>
<div class="str-outer"><div class="str-inner"><p class=" align-right">以上</p></div></div>
<div class="mod-list-02 of-notice"><ul class="list">
  <li><span class="mark">(注1)</span><div><small>防衛装備庁のプログラム</small></div></li>
</ul></div>
"""


def test_extract_nec_article_body_puts_subtitle_first_and_excludes_non_body() -> None:
    body = extract_nec_article_body(
        build_article('<span class="sub">～被災状況の把握を可能に～</span>', ARTICLE_BODY)
    )

    assert body == (
        "～被災状況の把握を可能に～\n"
        "2026年10月14日\n"
        "日本電気株式会社\n"
        "背景\n"
        "NECは、2026年に技術を開発しました(注1)。\n"
        "以上\n"
        "(注1)防衛装備庁のプログラム"
    )


def test_extract_nec_article_body_without_subtitle() -> None:
    body = extract_nec_article_body(build_article("", "<p>本文です。</p>"))

    assert body == "本文です。"


def test_extract_nec_article_body_raises_when_main_column_missing() -> None:
    with pytest.raises(ArticleContentUnavailableError, match="本文の領域が見つかりません"):
        extract_nec_article_body("<html><body><p>本文</p></body></html>")


def test_extract_nec_article_body_raises_when_body_is_empty() -> None:
    with pytest.raises(ArticleContentUnavailableError, match="本文が空です"):
        extract_nec_article_body(build_article("", ""))
