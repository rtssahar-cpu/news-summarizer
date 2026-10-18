import re
from collections.abc import Sequence

from bs4 import Tag
from bs4.element import Comment, NavigableString

WHITESPACE_PATTERN = re.compile(r"\s+")


def find_line_blocks(container: Tag, block_tags: Sequence[str]) -> list[Tag]:
    """1行の単位となるブロックを返す。<td>の中の<p>のように入れ子の場合は、内側だけを使って重複を避ける。"""
    return [
        block
        for block in container.find_all(list(block_tags))
        if block.find(list(block_tags)) is None
    ]


def to_lines(block: Tag) -> list[str]:
    """ブロック内のテキストを<br>の位置でだけ改行し、HTMLソース上の改行・空白は1つの空白にまとめる。

    本文は「<span>2026</span>年」のように1文の中が細かくタグで区切られていることがあるため、
    get_text("\\n") は使わない（文の途中で改行される）。
    """
    text = "".join(
        "\n" if isinstance(node, Tag) else WHITESPACE_PATTERN.sub(" ", node)
        for node in block.descendants
        if (isinstance(node, Tag) and node.name == "br")
        or (isinstance(node, NavigableString) and not isinstance(node, Comment))
    )
    return [line.strip() for line in text.split("\n") if line.strip()]


def is_inside_any(block: Tag, elements: Sequence[Tag]) -> bool:
    """ブロックが、いずれかの要素そのもの、またはその内側にあるかを返す。"""
    # BeautifulSoupのTagは == が内容の比較になるため、同一の要素かどうかは is で判定する
    ancestors_and_self = [block, *block.parents]
    return any(node is element for node in ancestors_and_self for element in elements)
