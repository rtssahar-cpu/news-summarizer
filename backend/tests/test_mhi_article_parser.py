import pytest

from app.interface_adapters.gateways.mhi_article_parser import extract_mhi_article_body
from app.use_cases.errors import ArticleContentUnavailableError

ARTICLE_HTML = """
<h1><div class="field--name-field-page-title">タイトル</div></h1>
<div class="field field--name-field-description field__item">
  <p>◆ リード文1<br>◆ リード文2</p>
</div>
<div class="field field--name-field-detail1 field__item">
  <p>本文の段落1</p><p>本文の段落2</p>
</div>
<div class="field field--name-field-detail2 field__item"><p>本文の続き</p></div>
<div class="field field--name-field-related-contact">お問い合わせ先</div>
"""


def test_extract_mhi_article_body_joins_description_and_detail_fields() -> None:
    body = extract_mhi_article_body(ARTICLE_HTML)

    assert body == "◆ リード文1\n◆ リード文2\n本文の段落1\n本文の段落2\n本文の続き"


def test_extract_mhi_article_body_works_without_description() -> None:
    html = '<div class="field--name-field-detail1"><p>本文のみ</p></div>'

    assert extract_mhi_article_body(html) == "本文のみ"


def test_extract_mhi_article_body_raises_when_detail_field_is_missing() -> None:
    html = '<div class="field--name-field-description"><p>リード文のみ</p></div>'

    with pytest.raises(ArticleContentUnavailableError, match="本文のフィールドが見つかりません"):
        extract_mhi_article_body(html)
