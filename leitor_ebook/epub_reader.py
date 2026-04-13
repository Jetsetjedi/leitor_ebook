"""EPUB format reader module."""

import re
from dataclasses import dataclass, field
from typing import List, Optional

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub


@dataclass
class Chapter:
    """Represents a single chapter of an EPUB book."""

    title: str
    content: str
    item_id: str


@dataclass
class EpubBook:
    """Represents a parsed EPUB book."""

    title: str
    author: str
    chapters: List[Chapter] = field(default_factory=list)
    cover_image: Optional[bytes] = None


def _html_to_text(html_content: bytes) -> str:
    """Convert HTML bytes to plain text, preserving paragraph structure."""
    soup = BeautifulSoup(html_content, "lxml")

    # Remove script and style elements
    for tag in soup(["script", "style"]):
        tag.decompose()

    paragraphs = []
    for element in soup.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "li"]):
        text = element.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            tag_name = element.name
            if tag_name == "h1":
                paragraphs.append(f"\n{'=' * 60}\n{text}\n{'=' * 60}\n")
            elif tag_name in ("h2", "h3"):
                paragraphs.append(f"\n{text}\n{'-' * len(text)}\n")
            elif tag_name in ("h4", "h5", "h6"):
                paragraphs.append(f"\n{text}\n")
            elif tag_name == "li":
                paragraphs.append(f"  • {text}")
            else:
                paragraphs.append(text)

    return "\n\n".join(paragraphs)


def load_epub(file_path: str) -> EpubBook:
    """Load and parse an EPUB file.

    Args:
        file_path: Path to the .epub file.

    Returns:
        An EpubBook instance with title, author, and chapters.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file cannot be parsed as a valid EPUB.
    """
    try:
        book = epub.read_epub(file_path)
    except Exception as exc:
        raise ValueError(f"Não foi possível abrir o arquivo EPUB: {exc}") from exc

    title = book.get_metadata("DC", "title")
    title = title[0][0] if title else "Título desconhecido"

    author = book.get_metadata("DC", "creator")
    author = author[0][0] if author else "Autor desconhecido"

    # Attempt to find cover image
    cover_image: Optional[bytes] = None
    for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
        name = item.get_name().lower()
        if "cover" in name:
            cover_image = item.get_content()
            break

    # Gather chapters in spine order
    chapters: List[Chapter] = []
    spine_ids = {item_id for item_id, _ in book.spine}

    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        if item.get_id() not in spine_ids:
            continue
        content = item.get_content()
        text = _html_to_text(content)
        if not text.strip():
            continue
        soup = BeautifulSoup(content, "lxml")
        heading = soup.find(["h1", "h2", "h3", "title"])
        chapter_title = heading.get_text(strip=True) if heading else item.get_name()
        chapters.append(
            Chapter(
                title=chapter_title,
                content=text,
                item_id=item.get_id(),
            )
        )

    return EpubBook(
        title=title,
        author=author,
        chapters=chapters,
        cover_image=cover_image,
    )
