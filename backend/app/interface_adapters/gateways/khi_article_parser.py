import re

from bs4 import BeautifulSoup, Tag
from bs4.element import Comment, NavigableString

from app.use_cases.errors import ArticleContentUnavailableError

# 副題（例: ～エンジン技術開発が前進～）はRSSのタイトルに含まれないため本文に加える
SUBTITLE_SELECTOR = "div.heading_subtitle"
DETAIL_AREA_SELECTOR = "div.news-detail-area"
# 本文は<p>と表のセル<td>で行が分かれる。行の中は「<span>2026</span>年」のように細かく区切られている
LINE_BLOCK_TAGS = ["p", "td", "li"]
WHITESPACE_PATTERN = re.compile(r"\s+")


def extract_khi_article_body(html: str) -> str:
    """記事ページの副題と本文を、改行でつないで返す。"""
    soup = BeautifulSoup(html, "html.parser")
    detail_area = soup.select_one(DETAIL_AREA_SELECTOR)
    if detail_area is None:
        raise ArticleContentUnavailableError("記事ページに本文の領域が見つかりません")

    detail_lines = [line for block in _find_line_blocks(detail_area) for line in _to_lines(block)]
    if not detail_lines:
        raise ArticleContentUnavailableError("記事ページの本文が空です")

    subtitle = soup.select_one(SUBTITLE_SELECTOR)
    subtitle_lines = _to_lines(subtitle) if subtitle is not None else []
    return "\n".join([*subtitle_lines, *detail_lines])


def _find_line_blocks(detail_area: Tag) -> list[Tag]:
    # <td>の中の<p>のように入れ子になっている場合は、内側だけを使って重複を避ける
    return [
        block
        for block in detail_area.find_all(LINE_BLOCK_TAGS)
        if block.find(LINE_BLOCK_TAGS) is None
    ]


def _to_lines(block: Tag) -> list[str]:
    """ブロック内のテキストを<br>の位置でだけ改行し、HTMLソース上の改行・空白は1つの空白にまとめる。"""
    text = "".join(
        "\n" if isinstance(node, Tag) else WHITESPACE_PATTERN.sub(" ", node)
        for node in block.descendants
        if (isinstance(node, Tag) and node.name == "br")
        or (isinstance(node, NavigableString) and not isinstance(node, Comment))
    )
    return [line.strip() for line in text.split("\n") if line.strip()]
