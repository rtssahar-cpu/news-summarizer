import pytest

from app.interface_adapters.gateways.khi_article_parser import extract_khi_article_body
from app.use_cases.errors import ArticleContentUnavailableError

ARTICLE_HTML = """
<div class="heading">
  <h1 class="heading_title">タイトル</h1>
  <div class="heading_subtitle">～副題～</div>
</div>
<p class="news-detail-date">2026年10月08日</p>
<div class="news-detail-area">
  <p></p>
  <p>本文の段落1</p>
  <p>本文の段落2<br>段落2の続き</p>
</div>
<div class="footer">お問い合わせ先</div>
"""


def test_extract_khi_article_body_joins_subtitle_and_detail_area() -> None:
    body = extract_khi_article_body(ARTICLE_HTML)

    assert body == "～副題～\n本文の段落1\n本文の段落2\n段落2の続き"


def test_extract_khi_article_body_keeps_inline_tags_in_one_line() -> None:
    html = """
    <div class="news-detail-area">
      <p>川崎重工は、<span>2026</span>年<span>10</span>月より<span><span>PPA</span></span><sup>※</sup>を
      開始しました。<!-- コメント --></p>
    </div>
    """

    assert extract_khi_article_body(html) == "川崎重工は、2026年10月よりPPA※を 開始しました。"


def test_extract_khi_article_body_reads_table_cells_as_lines() -> None:
    html = """
    <div class="news-detail-area">
      <p>概要</p>
      <table><tr><td><p>項目</p></td><td>名古屋第一工場<br /> （愛知県弥富市）</td></tr></table>
    </div>
    """

    assert extract_khi_article_body(html) == "概要\n項目\n名古屋第一工場\n（愛知県弥富市）"


def test_extract_khi_article_body_works_without_subtitle() -> None:
    html = '<div class="news-detail-area"><p>本文のみ</p></div>'

    assert extract_khi_article_body(html) == "本文のみ"


def test_extract_khi_article_body_raises_when_detail_area_is_missing() -> None:
    html = '<div class="heading_subtitle">～副題のみ～</div>'

    with pytest.raises(ArticleContentUnavailableError, match="本文の領域が見つかりません"):
        extract_khi_article_body(html)


def test_extract_khi_article_body_raises_when_detail_area_is_empty() -> None:
    html = '<div class="news-detail-area"><p></p></div>'

    with pytest.raises(ArticleContentUnavailableError, match="本文が空です"):
        extract_khi_article_body(html)
