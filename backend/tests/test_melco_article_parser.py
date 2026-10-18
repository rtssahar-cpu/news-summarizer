import pytest

from app.interface_adapters.gateways.melco_article_parser import extract_melco_split_pdf_urls
from app.use_cases.errors import ArticleContentUnavailableError

BASE_URL = "https://www.mitsubishielectric.co.jp"


def build_article_html(*hrefs: str) -> str:
    links = "".join(f'<li><a href="{href}">資料</a></li>' for href in hrefs)
    return f'<html><body><div class="article-header">見出し</div><ul>{links}</ul></body></html>'


def test_extract_melco_split_pdf_urls_returns_split_pdfs_in_page_order() -> None:
    html = build_article_html(
        "/ja/pr/2026/pdf/0820_ei1.pdf",
        "/ja/pr/2026/pdf/0820_ei2.pdf",
        # ホスト名の大文字・小文字が異なる絶対URLや、同じPDFへの重複リンクもある
        "https://www.MitsubishiElectric.co.jp/ja/pr/2026/pdf/0820_ei3.pdf",
        "/ja/pr/2026/pdf/0820_ei1.pdf",
    )

    assert extract_melco_split_pdf_urls(html, f"{BASE_URL}/ja/pr/2026/pdf/0820_ei.pdf") == [
        f"{BASE_URL}/ja/pr/2026/pdf/0820_ei1.pdf",
        f"{BASE_URL}/ja/pr/2026/pdf/0820_ei2.pdf",
        f"{BASE_URL}/ja/pr/2026/pdf/0820_ei3.pdf",
    ]


def test_extract_melco_split_pdf_urls_supports_hyphenated_suffix() -> None:
    html = build_article_html("/ja/pr/2025/pdf/0909-1.pdf", "/ja/pr/2025/pdf/0909-2.pdf")

    assert extract_melco_split_pdf_urls(html, f"{BASE_URL}/ja/pr/2025/pdf/0909.pdf") == [
        f"{BASE_URL}/ja/pr/2025/pdf/0909-1.pdf",
        f"{BASE_URL}/ja/pr/2025/pdf/0909-2.pdf",
    ]


def test_extract_melco_split_pdf_urls_ignores_links_to_other_articles() -> None:
    html = build_article_html(
        # 注釈で参照される過去の発表や、IDの先頭が同じ別の記事
        "https://www.MitsubishiElectric.co.jp/ja/pr/2024/pdf/1115-b.pdf",
        "/ja/pr/2026/pdf/0820_eia.pdf",
        "/ja/pr/2026/pdf/0820_ei1.pdf",
    )

    assert extract_melco_split_pdf_urls(html, f"{BASE_URL}/ja/pr/2026/pdf/0820_ei.pdf") == [
        f"{BASE_URL}/ja/pr/2026/pdf/0820_ei1.pdf"
    ]


def test_extract_melco_split_pdf_urls_raises_when_no_split_pdf_found() -> None:
    html = build_article_html("/ja/pr/2024/pdf/1115-b.pdf")

    with pytest.raises(
        ArticleContentUnavailableError, match="分割されたPDFへのリンクが見つかりません"
    ):
        extract_melco_split_pdf_urls(html, f"{BASE_URL}/ja/pr/2026/pdf/0820_ei.pdf")
