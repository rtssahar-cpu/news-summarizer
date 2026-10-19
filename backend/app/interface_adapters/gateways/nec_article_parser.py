from bs4 import BeautifulSoup

from app.interface_adapters.gateways.html_text import find_line_blocks, is_inside_any, to_lines
from app.use_cases.errors import ArticleContentUnavailableError

MAIN_COLUMN_SELECTOR = "div.str-column-main"
# 副題（例: ～多様な被災状況の把握を可能にし、…～）はRSSのタイトルに含まれないため本文に加える。
# 副題は本文の領域の外（ページタイトルの領域）にある
SUBTITLE_SELECTOR = "div.str-pageTitle span.sub"
# SNSの共有ボタン（div.comp-sns）、末尾の定型文（div.mod-box）は本文ではない。
# 「以上」の後の注記（注1〜）は装備品の補足等を含むことがあるため本文として残す
NON_BODY_SELECTOR = "div.comp-sns, div.mod-box"
# 小見出し（<h2>〜<h4>）も本文の一部として1行ずつ取り出す
LINE_BLOCK_TAGS = ["p", "td", "li", "dt", "dd", "h2", "h3", "h4"]


def extract_nec_article_body(html: str) -> str:
    """記事ページの副題と本文を、改行でつないで返す。"""
    soup = BeautifulSoup(html, "html.parser")
    main_column = soup.select_one(MAIN_COLUMN_SELECTOR)
    if main_column is None:
        raise ArticleContentUnavailableError("記事ページに本文の領域が見つかりません")

    non_body_elements = main_column.select(NON_BODY_SELECTOR)
    body_lines = [
        line
        for block in find_line_blocks(main_column, LINE_BLOCK_TAGS)
        if not is_inside_any(block, non_body_elements)
        for line in to_lines(block)
    ]
    if not body_lines:
        raise ArticleContentUnavailableError("記事ページの本文が空です")

    subtitle = soup.select_one(SUBTITLE_SELECTOR)
    subtitle_lines = to_lines(subtitle) if subtitle is not None else []
    return "\n".join([*subtitle_lines, *body_lines])
