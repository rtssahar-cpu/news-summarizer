import pytest

from app.interface_adapters.gateways.pdf_text import extract_pdf_text
from app.use_cases.errors import ArticleContentUnavailableError
from tests.conftest import build_minimal_pdf


def test_extract_pdf_text_returns_page_text() -> None:
    pdf_bytes = build_minimal_pdf("Hello Test")

    assert extract_pdf_text(pdf_bytes) == "Hello Test"


@pytest.mark.parametrize("broken_pdf_bytes", [b"", b"not a pdf", b"%PDF-1.4\n broken"])
def test_extract_pdf_text_raises_article_content_unavailable_error_for_broken_pdf(
    broken_pdf_bytes: bytes,
) -> None:
    with pytest.raises(ArticleContentUnavailableError):
        extract_pdf_text(broken_pdf_bytes)
