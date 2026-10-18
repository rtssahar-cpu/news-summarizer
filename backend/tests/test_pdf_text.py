import secrets
from io import BytesIO

import pytest
from pypdf import PdfWriter
from pypdf.errors import DependencyError

from app.interface_adapters.gateways import pdf_text
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


def _encrypt_pdf_with_aes(pdf_bytes: bytes) -> bytes:
    """日立のPDFと同様に、閲覧用パスワードなし・権限制限用のパスワードありでAES暗号化する。"""
    writer = PdfWriter(clone_from=BytesIO(pdf_bytes))
    writer.encrypt(user_password="", owner_password=secrets.token_hex(8), algorithm="AES-256")
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_extract_pdf_text_returns_text_of_aes_encrypted_pdf() -> None:
    encrypted_pdf_bytes = _encrypt_pdf_with_aes(build_minimal_pdf("Hello Test"))

    assert extract_pdf_text(encrypted_pdf_bytes) == "Hello Test"


def test_extract_pdf_text_raises_article_content_unavailable_error_for_dependency_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_dependency_error(_stream: BytesIO) -> None:
        raise DependencyError("cryptography>=3.1 is required for AES algorithm")

    monkeypatch.setattr(pdf_text, "PdfReader", raise_dependency_error)

    with pytest.raises(ArticleContentUnavailableError) as error_info:
        extract_pdf_text(build_minimal_pdf("Hello Test"))
    assert isinstance(error_info.value.__cause__, DependencyError)
