from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from app.use_cases.errors import ArticleContentUnavailableError


def extract_pdf_text(pdf_bytes: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        pages_text = [page.extract_text() or "" for page in reader.pages]
    except PyPdfError as error:
        raise ArticleContentUnavailableError(f"PDFからテキストを抽出できません: {error}") from error
    return "\n".join(pages_text).strip()
