import pytest

from app.interface_adapters.gateways.subaru_article_parser import extract_subaru_article_body
from app.use_cases.errors import ArticleContentUnavailableError

ARTICLE_HTML = """
<div id="text">
  <div class="newsHeader">
    <div class="date">2026年10月5日</div>
    <ul class="headBtns"><li class="print"><button>ページを印刷する</button></li></ul>
  </div>
  <h1>
    <div class="component-newsList"><ul><li><span>モーターショー</span></li></ul></div>
    SUBARU 「Japan Mobility Show Bizweek 2026」出展概要
  </h1>
  <!-- 本文 -->
  <p>SUBARUは、幕張メッセにて開催される展示会に出展します。</p>
  <table><tbody><tr>
    <td><img src="booth.webp" alt=""><p>SUBARUブースイメージ</p></td>
  </tr></tbody></table>
  <p>減価ゼロ<sup>*1</sup>の発想に基づく機能拡張を展示します。<br>
  安心と愉しさを提供します。</p>
  <div>
    <div>*1：クルマの購入後も価値を維持・向上させ続けるという考え方。</div>
  </div>
  <!-- //本文 -->
  <div class="newsFooter"><a href="/pdf/news/sample.pdf">[PDF/268 KB]</a></div>
</div>
<div id="external"><p>関連リリース</p></div>
"""


def test_extract_subaru_article_body_excludes_header_title_and_footer() -> None:
    body = extract_subaru_article_body(ARTICLE_HTML)

    assert body == (
        "SUBARUは、幕張メッセにて開催される展示会に出展します。\n"
        "SUBARUブースイメージ\n"
        "減価ゼロ*1の発想に基づく機能拡張を展示します。\n"
        "安心と愉しさを提供します。\n"
        "*1：クルマの購入後も価値を維持・向上させ続けるという考え方。"
    )


def test_extract_subaru_article_body_raises_when_text_area_missing() -> None:
    with pytest.raises(ArticleContentUnavailableError, match="本文の領域が見つかりません"):
        extract_subaru_article_body("<html><body><p>本文</p></body></html>")


def test_extract_subaru_article_body_raises_when_body_is_empty() -> None:
    html = '<div id="text"><div class="newsHeader"><div>2026年10月5日</div></div><h1>題</h1></div>'

    with pytest.raises(ArticleContentUnavailableError, match="本文が空です"):
        extract_subaru_article_body(html)
