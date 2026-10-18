from bs4 import BeautifulSoup

from app.use_cases.errors import ArticleContentUnavailableError

DESCRIPTION_FIELD_SELECTOR = "div.field--name-field-description"
# 本文は detail1, detail2, ... と複数のフィールドに分かれることがあるため前方一致で選ぶ
DETAIL_FIELD_SELECTOR = "div[class*='field--name-field-detail']"


def extract_mhi_article_body(html: str) -> str:
    """記事ページのリード文と本文を、ページ内の出現順に改行でつないで返す。"""
    soup = BeautifulSoup(html, "html.parser")
    if soup.select_one(DETAIL_FIELD_SELECTOR) is None:
        raise ArticleContentUnavailableError("記事ページに本文のフィールドが見つかりません")

    body_fields = soup.select(f"{DESCRIPTION_FIELD_SELECTOR}, {DETAIL_FIELD_SELECTOR}")
    texts = [text for field in body_fields if (text := field.get_text("\n", strip=True))]
    return "\n".join(texts)
