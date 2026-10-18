import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.interface_adapters.gateways.melco_news_parser import BASE_URL
from app.use_cases.errors import ArticleContentUnavailableError

# 決算・子会社化等の記事は「リリース全文」PDFがなく（記事URLから導いたPDFは404）、本文の代わりに
# 分割されたPDFへのリンクが並ぶ（例: 0820_ei.pdf に対して 0820_ei1.pdf〜0820_ei4.pdf、
# 0909.pdf に対して 0909-1.pdf〜）。リンクにはホスト名の大文字・小文字が異なる絶対URLも
# 混ざるため、パスで比較する
SPLIT_PDF_SUFFIX_PATTERN = r"-?\d+\.pdf"


def extract_melco_split_pdf_urls(html: str, pdf_url: str) -> list[str]:
    """記事ページから、分割されたPDFのURLをページ内の順に（重複なしで）返す。

    pdf_url は記事URLから導いた（存在しない）「リリース全文」PDFのURL。
    """
    pdf_stem = urlparse(pdf_url).path.removesuffix(".pdf")
    split_pdf_path_pattern = re.compile(rf"^{re.escape(pdf_stem)}{SPLIT_PDF_SUFFIX_PATTERN}$")

    soup = BeautifulSoup(html, "html.parser")
    link_paths = [
        urlparse(urljoin(BASE_URL, str(link["href"]))).path for link in soup.select("a[href]")
    ]
    split_pdf_paths = [path for path in link_paths if split_pdf_path_pattern.match(path)]
    if not split_pdf_paths:
        raise ArticleContentUnavailableError("記事ページに分割されたPDFへのリンクが見つかりません")

    return [f"{BASE_URL}{path}" for path in dict.fromkeys(split_pdf_paths)]
