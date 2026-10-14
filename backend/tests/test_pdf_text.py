from app.interface_adapters.gateways.pdf_text import extract_pdf_text
from tests.conftest import build_minimal_pdf


def test_extract_pdf_text_returns_page_text() -> None:
    pdf_bytes = build_minimal_pdf("Hello Test")

    assert extract_pdf_text(pdf_bytes) == "Hello Test"
