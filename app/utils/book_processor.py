"""
Processadores de conteúdo por formato de ebook.

PDF  → PyMuPDF (fitz)
EPUB → ebooklib + BeautifulSoup
MOBI → mobi (python-mobi)
TXT  → leitura direta UTF-8
"""
import html
import re
from pathlib import Path


# ── PDF ────────────────────────────────────────────────────────────────────────

def extract_pdf_page(filepath: str, page_number: int) -> dict:
    """Extrai página de PDF como HTML seguro. page_number é 0-indexed."""
    import fitz  # PyMuPDF

    doc = fitz.open(filepath)
    total = doc.page_count
    page_number = max(0, min(page_number, total - 1))
    page = doc.load_page(page_number)

    blocks = page.get_text("blocks")
    paragraphs = []
    for b in blocks:
        text = b[4].strip()
        if text:
            paragraphs.append(f"<p>{html.escape(text)}</p>")

    doc.close()
    return {
        "content": "\n".join(paragraphs),
        "current_page": page_number,
        "total_pages": total,
    }


def get_pdf_toc(filepath: str) -> list:
    import fitz
    doc = fitz.open(filepath)
    toc = [{"level": t[0], "title": t[1], "page": t[2]} for t in doc.get_toc()]
    doc.close()
    return toc


# ── EPUB ───────────────────────────────────────────────────────────────────────

def extract_epub_chapter(filepath: str, chapter_index: int) -> dict:
    from ebooklib import epub, ITEM_DOCUMENT
    from bs4 import BeautifulSoup

    book = epub.read_epub(filepath)
    chapters = [item for item in book.get_items() if item.get_type() == ITEM_DOCUMENT]
    total = len(chapters)
    chapter_index = max(0, min(chapter_index, total - 1))

    raw_html = chapters[chapter_index].get_content().decode("utf-8", errors="replace")
    soup = BeautifulSoup(raw_html, "html.parser")

    # Remove scripts e estilos do EPUB (XSS prevention)
    for tag in soup(["script", "style", "link", "iframe", "object", "embed"]):
        tag.decompose()

    # Remove atributos perigosos
    for tag in soup.find_all(True):
        for attr in ["onclick", "onload", "onerror", "onmouseover", "href"]:
            if tag.has_attr(attr):
                if attr == "href" and not tag[attr].startswith(("http", "#")):
                    del tag[attr]
                elif attr != "href":
                    del tag[attr]

    content = str(soup.body or soup)

    return {
        "content": content,
        "current_page": chapter_index,
        "total_pages": total,
        "title": chapters[chapter_index].get_name(),
    }


def get_epub_toc(filepath: str) -> list:
    from ebooklib import epub, ITEM_DOCUMENT
    book = epub.read_epub(filepath)
    toc = []
    for i, item in enumerate(book.get_items()):
        if item.get_type() == ITEM_DOCUMENT:
            toc.append({"index": i, "title": item.get_name()})
    return toc


# ── MOBI ───────────────────────────────────────────────────────────────────────

def extract_mobi_text(filepath: str, page: int = 0, page_size: int = 3000) -> dict:
    """
    Extrai texto de MOBI e divide em 'páginas' virtuais de page_size caracteres.
    """
    import mobi
    from bs4 import BeautifulSoup

    _, extracted_path = mobi.extract(filepath)
    html_files = list(Path(extracted_path).rglob("*.html")) + \
                 list(Path(extracted_path).rglob("*.htm"))

    full_text = ""
    for hf in html_files:
        soup = BeautifulSoup(hf.read_text(errors="replace"), "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        full_text += soup.get_text(" ", strip=True) + "\n\n"

    pages = _paginate(full_text, page_size)
    total = len(pages)
    page = max(0, min(page, total - 1))
    content = f"<p>{html.escape(pages[page])}</p>" if pages else "<p></p>"

    return {"content": content, "current_page": page, "total_pages": total}


# ── TXT ────────────────────────────────────────────────────────────────────────

def extract_txt_page(filepath: str, page: int = 0, page_size: int = 3000) -> dict:
    text = Path(filepath).read_text(encoding="utf-8", errors="replace")
    pages = _paginate(text, page_size)
    total = len(pages)
    page = max(0, min(page, total - 1))
    content = f"<p>{html.escape(pages[page])}</p>" if pages else "<p></p>"
    return {"content": content, "current_page": page, "total_pages": total}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _paginate(text: str, size: int) -> list:
    if not text.strip():
        return [""]
    return [text[i:i + size] for i in range(0, len(text), size)]


def search_in_book(filepath: str, fmt: str, query: str) -> list:
    """Busca texto no livro e retorna lista de resultados com contexto."""
    if not query or len(query) > 200:
        return []

    query_lower = query.lower()
    results = []

    if fmt == "pdf":
        import fitz
        doc = fitz.open(filepath)
        for i, page in enumerate(doc):
            text = page.get_text()
            if query_lower in text.lower():
                idx = text.lower().find(query_lower)
                snippet = text[max(0, idx - 60): idx + 60 + len(query)].strip()
                results.append({"page": i, "snippet": html.escape(snippet)})
        doc.close()

    elif fmt == "epub":
        from ebooklib import epub, ITEM_DOCUMENT
        from bs4 import BeautifulSoup
        book = epub.read_epub(filepath)
        for i, item in enumerate(item for item in book.get_items()
                                  if item.get_type() == ITEM_DOCUMENT):
            raw = item.get_content().decode("utf-8", errors="replace")
            text = BeautifulSoup(raw, "html.parser").get_text()
            if query_lower in text.lower():
                idx = text.lower().find(query_lower)
                snippet = text[max(0, idx - 60): idx + 60 + len(query)].strip()
                results.append({"page": i, "snippet": html.escape(snippet)})

    elif fmt in ("txt", "mobi"):
        filepath_obj = Path(filepath)
        if fmt == "txt":
            text = filepath_obj.read_text(encoding="utf-8", errors="replace")
        else:
            text = filepath_obj.read_text(errors="replace")
        pages = _paginate(text, 3000)
        for i, chunk in enumerate(pages):
            if query_lower in chunk.lower():
                idx = chunk.lower().find(query_lower)
                snippet = chunk[max(0, idx - 60): idx + 60 + len(query)].strip()
                results.append({"page": i, "snippet": html.escape(snippet)})

    return results[:50]  # limita resultados
