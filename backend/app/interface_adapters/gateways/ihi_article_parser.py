from bs4 import BeautifulSoup

from app.interface_adapters.gateways.html_text import find_line_blocks, is_inside_any, to_lines
from app.use_cases.errors import ArticleContentUnavailableError

DETAIL_AREA_SELECTOR = "div.m-entry-detail"
# 副題（例: ～液化水素基地で安定操業に貢献～）は一覧のタイトルに含まれないため本文に加える。
# 副題のない記事でも空の <div class="size-xsmall"> は置かれている
SUBTITLE_SELECTOR = "header.m-entry-detail_title h1 > div.size-xsmall"
# 日付・タイトル（header）、英語版へのリンク（p.m-en-link）、「ニューストップへ」は本文ではない
NON_BODY_SELECTOR = "header.m-entry-detail_title, p.m-en-link, p.m-entry-detail_back"
# 小見出し（<h4>）や特長の一覧（<dl>）も本文の一部として1行ずつ取り出す
LINE_BLOCK_TAGS = ["p", "td", "li", "dt", "dd", "h3", "h4"]


def extract_ihi_article_body(html: str) -> str:
    """記事ページの副題と本文を、改行でつないで返す。"""
    soup = BeautifulSoup(html, "html.parser")
    detail_area = soup.select_one(DETAIL_AREA_SELECTOR)
    if detail_area is None:
        raise ArticleContentUnavailableError("記事ページに本文の領域が見つかりません")

    non_body_elements = detail_area.select(NON_BODY_SELECTOR)
    body_lines = [
        line
        for block in find_line_blocks(detail_area, LINE_BLOCK_TAGS)
        if not is_inside_any(block, non_body_elements)
        for line in to_lines(block)
    ]
    if not body_lines:
        raise ArticleContentUnavailableError("記事ページの本文が空です")

    subtitle = detail_area.select_one(SUBTITLE_SELECTOR)
    subtitle_lines = to_lines(subtitle) if subtitle is not None else []
    return "\n".join([*subtitle_lines, *body_lines])
