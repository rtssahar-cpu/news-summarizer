from bs4 import BeautifulSoup

from app.interface_adapters.gateways.html_text import find_line_blocks, is_inside_any, to_lines
from app.use_cases.errors import ArticleContentUnavailableError

# 本文を囲む要素はなく、日付・タイトル・本文・PDFボタンが div#text の直下に並んでいる
TEXT_AREA_SELECTOR = "div#text"
# 日付（div.newsHeader）、カテゴリ付きのタイトル（h1）、PDFボタン（div.newsFooter）は本文ではない
NON_BODY_SELECTOR = "div.newsHeader, h1, div.newsFooter"
# 注釈（*1：...）は<div>で1行ずつ書かれているため、<div>も行の単位にする
LINE_BLOCK_TAGS = ["p", "td", "li", "div"]


def extract_subaru_article_body(html: str) -> str:
    """記事ページの本文を、行ごとに改行でつないで返す。"""
    soup = BeautifulSoup(html, "html.parser")
    text_area = soup.select_one(TEXT_AREA_SELECTOR)
    if text_area is None:
        raise ArticleContentUnavailableError("記事ページに本文の領域が見つかりません")

    non_body_elements = text_area.select(NON_BODY_SELECTOR)
    body_lines = [
        line
        for block in find_line_blocks(text_area, LINE_BLOCK_TAGS)
        if not is_inside_any(block, non_body_elements)
        for line in to_lines(block)
    ]
    if not body_lines:
        raise ArticleContentUnavailableError("記事ページの本文が空です")
    return "\n".join(body_lines)
