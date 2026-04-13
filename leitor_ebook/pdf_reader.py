"""PDF format reader module."""

from dataclasses import dataclass, field
from typing import List, Optional

import fitz  # PyMuPDF


@dataclass
class PdfPage:
    """Represents a single page of a PDF document."""

    number: int
    text: str


@dataclass
class PdfBook:
    """Represents a parsed PDF document."""

    title: str
    author: str
    pages: List[PdfPage] = field(default_factory=list)
    cover_image: Optional[bytes] = None

    @property
    def total_pages(self) -> int:
        """Return the total number of pages."""
        return len(self.pages)


def load_pdf(file_path: str) -> PdfBook:
    """Load and parse a PDF file.

    Args:
        file_path: Path to the .pdf file.

    Returns:
        A PdfBook instance with metadata and pages.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file cannot be parsed as a valid PDF.
    """
    try:
        doc = fitz.open(file_path)
    except Exception as exc:
        raise ValueError(f"Não foi possível abrir o arquivo PDF: {exc}") from exc

    metadata = doc.metadata or {}
    title = metadata.get("title") or "Título desconhecido"
    author = metadata.get("author") or "Autor desconhecido"

    # Extract cover as PNG bytes from the first page thumbnail
    cover_image: Optional[bytes] = None
    if len(doc) > 0:
        first_page = doc[0]
        matrix = fitz.Matrix(0.5, 0.5)
        pix = first_page.get_pixmap(matrix=matrix)
        cover_image = pix.tobytes("png")

    pages: List[PdfPage] = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        pages.append(PdfPage(number=page_num + 1, text=text))

    doc.close()

    return PdfBook(
        title=title,
        author=author,
        pages=pages,
        cover_image=cover_image,
    )
