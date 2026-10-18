from bs4 import BeautifulSoup

from app.interface_adapters.gateways.html_text import find_line_blocks, to_lines
from app.use_cases.errors import ArticleContentUnavailableError

# 副題（例: ～エンジン技術開発が前進～）はRSSのタイトルに含まれないため本文に加える
SUBTITLE_SELECTOR = "div.heading_subtitle"
DETAIL_AREA_SELECTOR = "div.news-detail-area"
# 本文は<p>と表のセル<td>で行が分かれる。行の中は「<span>2026</span>年」のように細かく区切られている
LINE_BLOCK_TAGS = ["p", "td", "li"]


def extract_khi_article_body(html: str) -> str:
    """記事ページの副題と本文を、改行でつないで返す。"""
    soup = BeautifulSoup(html, "html.parser")
    detail_area = soup.select_one(DETAIL_AREA_SELECTOR)
    if detail_area is None:
        raise ArticleContentUnavailableError("記事ページに本文の領域が見つかりません")

    detail_lines = [
        line for block in find_line_blocks(detail_area, LINE_BLOCK_TAGS) for line in to_lines(block)
    ]
    if not detail_lines:
        raise ArticleContentUnavailableError("記事ページの本文が空です")

    subtitle = soup.select_one(SUBTITLE_SELECTOR)
    subtitle_lines = to_lines(subtitle) if subtitle is not None else []
    return "\n".join([*subtitle_lines, *detail_lines])
