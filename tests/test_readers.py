"""Tests for the EPUB and PDF reader modules and bookmarks."""

import io
import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from leitor_ebook.bookmarks import (
    Bookmark,
    add_bookmark,
    add_recent_file,
    get_bookmarks,
    get_recent_files,
    remove_bookmark,
)
from leitor_ebook.epub_reader import Chapter, EpubBook, _html_to_text, load_epub
from leitor_ebook.pdf_reader import PdfBook, PdfPage, load_pdf


# ---------------------------------------------------------------------------
# HTML to text conversion
# ---------------------------------------------------------------------------

class TestHtmlToText(unittest.TestCase):
    def test_paragraph_extraction(self):
        html = b"<html><body><p>Hello world</p></body></html>"
        result = _html_to_text(html)
        self.assertIn("Hello world", result)

    def test_heading_h1(self):
        html = b"<html><body><h1>Chapter One</h1><p>Text here</p></body></html>"
        result = _html_to_text(html)
        self.assertIn("Chapter One", result)
        self.assertIn("=", result)  # h1 gets underlined with '='

    def test_heading_h2(self):
        html = b"<html><body><h2>Section</h2></body></html>"
        result = _html_to_text(html)
        self.assertIn("Section", result)
        self.assertIn("-", result)

    def test_list_items(self):
        html = b"<html><body><ul><li>Item A</li><li>Item B</li></ul></body></html>"
        result = _html_to_text(html)
        self.assertIn("• Item A", result)
        self.assertIn("• Item B", result)

    def test_script_style_removed(self):
        html = b"<html><head><style>body{color:red}</style></head><body><script>alert(1)</script><p>Clean</p></body></html>"
        result = _html_to_text(html)
        self.assertNotIn("alert", result)
        self.assertNotIn("color:red", result)
        self.assertIn("Clean", result)

    def test_empty_html(self):
        html = b"<html><body></body></html>"
        result = _html_to_text(html)
        self.assertEqual(result, "")

    def test_whitespace_normalised(self):
        html = b"<html><body><p>  Multiple   spaces   here  </p></body></html>"
        result = _html_to_text(html)
        self.assertNotIn("   ", result)


# ---------------------------------------------------------------------------
# EPUB reader
# ---------------------------------------------------------------------------

class TestLoadEpub(unittest.TestCase):
    def _make_mock_item(self, item_id, name, content, media_type="application/xhtml+xml"):
        item = MagicMock()
        item.get_id.return_value = item_id
        item.get_name.return_value = name
        item.get_content.return_value = content
        item.media_type = media_type
        return item

    @patch("leitor_ebook.epub_reader.epub.read_epub")
    def test_basic_epub_loading(self, mock_read):
        book = MagicMock()
        book.get_metadata.side_effect = lambda ns, key: (
            [("My Book", {})] if key == "title" else [("Author Name", {})]
        )
        book.spine = [("ch1", "yes")]

        chapter_item = self._make_mock_item(
            "ch1", "chapter1.xhtml",
            b"<html><body><h1>Chapter 1</h1><p>Content here.</p></body></html>",
        )
        cover_item = self._make_mock_item(
            "cover", "cover.jpg", b"\x89PNG\r\n", "image/jpeg"
        )
        cover_item.get_name.return_value = "cover.jpg"

        import ebooklib
        def get_items_of_type(itype):
            if itype == ebooklib.ITEM_DOCUMENT:
                return [chapter_item]
            if itype == ebooklib.ITEM_IMAGE:
                return [cover_item]
            return []

        book.get_items_of_type.side_effect = get_items_of_type
        mock_read.return_value = book

        result = load_epub("fake.epub")
        self.assertIsInstance(result, EpubBook)
        self.assertEqual(result.title, "My Book")
        self.assertEqual(result.author, "Author Name")
        self.assertEqual(len(result.chapters), 1)
        self.assertIn("Content here", result.chapters[0].content)

    @patch("leitor_ebook.epub_reader.epub.read_epub")
    def test_missing_metadata_uses_defaults(self, mock_read):
        book = MagicMock()
        book.get_metadata.return_value = []
        book.spine = []

        import ebooklib
        book.get_items_of_type.return_value = []
        mock_read.return_value = book

        result = load_epub("fake.epub")
        self.assertEqual(result.title, "Título desconhecido")
        self.assertEqual(result.author, "Autor desconhecido")
        self.assertEqual(result.chapters, [])

    @patch("leitor_ebook.epub_reader.epub.read_epub", side_effect=Exception("bad file"))
    def test_invalid_file_raises_value_error(self, _mock):
        with self.assertRaises(ValueError):
            load_epub("invalid.epub")

    @patch("leitor_ebook.epub_reader.epub.read_epub")
    def test_skips_chapters_not_in_spine(self, mock_read):
        book = MagicMock()
        book.get_metadata.side_effect = lambda ns, key: (
            [("Book", {})] if key == "title" else [("Auth", {})]
        )
        book.spine = [("ch1", "yes")]  # only ch1 is in spine

        ch1 = self._make_mock_item(
            "ch1", "ch1.xhtml",
            b"<html><body><p>In spine</p></body></html>",
        )
        ch2 = self._make_mock_item(
            "ch2", "ch2.xhtml",
            b"<html><body><p>Not in spine</p></body></html>",
        )

        import ebooklib
        def get_items_of_type(itype):
            if itype == ebooklib.ITEM_DOCUMENT:
                return [ch1, ch2]
            return []

        book.get_items_of_type.side_effect = get_items_of_type
        mock_read.return_value = book

        result = load_epub("fake.epub")
        self.assertEqual(len(result.chapters), 1)
        self.assertIn("In spine", result.chapters[0].content)


# ---------------------------------------------------------------------------
# PDF reader
# ---------------------------------------------------------------------------

class TestLoadPdf(unittest.TestCase):
    @patch("leitor_ebook.pdf_reader.fitz.open")
    def test_basic_pdf_loading(self, mock_open):
        doc = MagicMock()
        doc.__len__.return_value = 2
        doc.metadata = {"title": "My PDF", "author": "PDF Author"}

        page0 = MagicMock()
        page0.get_text.return_value = "Page one content"
        pix0 = MagicMock()
        pix0.tobytes.return_value = b"PNGDATA"
        page0.get_pixmap.return_value = pix0

        page1 = MagicMock()
        page1.get_text.return_value = "Page two content"

        doc.__getitem__ = lambda self, idx: page0 if idx == 0 else page1
        mock_open.return_value = doc

        result = load_pdf("fake.pdf")
        self.assertIsInstance(result, PdfBook)
        self.assertEqual(result.title, "My PDF")
        self.assertEqual(result.author, "PDF Author")
        self.assertEqual(result.total_pages, 2)
        self.assertEqual(result.pages[0].text, "Page one content")
        self.assertEqual(result.pages[1].text, "Page two content")
        doc.close.assert_called_once()

    @patch("leitor_ebook.pdf_reader.fitz.open")
    def test_missing_metadata_uses_defaults(self, mock_open):
        doc = MagicMock()
        doc.__len__.return_value = 0
        doc.metadata = {}

        mock_open.return_value = doc

        result = load_pdf("fake.pdf")
        self.assertEqual(result.title, "Título desconhecido")
        self.assertEqual(result.author, "Autor desconhecido")
        self.assertEqual(result.total_pages, 0)

    @patch("leitor_ebook.pdf_reader.fitz.open", side_effect=Exception("cannot open"))
    def test_invalid_file_raises_value_error(self, _mock):
        with self.assertRaises(ValueError):
            load_pdf("invalid.pdf")

    @patch("leitor_ebook.pdf_reader.fitz.open")
    def test_page_numbers_are_one_based(self, mock_open):
        doc = MagicMock()
        doc.__len__.return_value = 3
        doc.metadata = {}

        page = MagicMock()
        page.get_text.return_value = "text"
        pix = MagicMock()
        pix.tobytes.return_value = b""
        page.get_pixmap.return_value = pix
        doc.__getitem__ = lambda self, idx: page

        mock_open.return_value = doc

        result = load_pdf("fake.pdf")
        self.assertEqual([p.number for p in result.pages], [1, 2, 3])


# ---------------------------------------------------------------------------
# Bookmarks
# ---------------------------------------------------------------------------

class TestBookmarks(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=".json", mode="w", encoding="utf-8"
        )
        self._tmp.write('{"bookmarks": [], "recent_files": []}')
        self._tmp.close()
        self._patcher = patch(
            "leitor_ebook.bookmarks._BOOKMARKS_FILE", self._tmp.name
        )
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        os.unlink(self._tmp.name)

    def test_add_and_get_bookmark(self):
        bm = Bookmark(file_path="/book.epub", position=3, label="Chapter 3")
        add_bookmark(bm)
        results = get_bookmarks("/book.epub")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].label, "Chapter 3")
        self.assertEqual(results[0].position, 3)

    def test_no_duplicate_bookmarks(self):
        bm = Bookmark(file_path="/book.epub", position=3, label="Ch 3")
        add_bookmark(bm)
        add_bookmark(bm)
        results = get_bookmarks("/book.epub")
        self.assertEqual(len(results), 1)

    def test_remove_bookmark(self):
        bm = Bookmark(file_path="/book.epub", position=5, label="Ch 5")
        add_bookmark(bm)
        remove_bookmark("/book.epub", 5)
        self.assertEqual(get_bookmarks("/book.epub"), [])

    def test_get_bookmarks_only_for_file(self):
        add_bookmark(Bookmark(file_path="/a.epub", position=0, label="A"))
        add_bookmark(Bookmark(file_path="/b.epub", position=0, label="B"))
        self.assertEqual(len(get_bookmarks("/a.epub")), 1)
        self.assertEqual(len(get_bookmarks("/b.epub")), 1)

    def test_recent_files(self):
        add_recent_file("/book1.epub")
        add_recent_file("/book2.epub")
        recent = get_recent_files()
        self.assertEqual(recent[0], "/book2.epub")
        self.assertEqual(recent[1], "/book1.epub")

    def test_recent_files_deduplication(self):
        add_recent_file("/book.epub")
        add_recent_file("/other.epub")
        add_recent_file("/book.epub")
        recent = get_recent_files()
        self.assertEqual(recent[0], "/book.epub")
        self.assertEqual(recent.count("/book.epub"), 1)

    def test_recent_files_max_limit(self):
        for i in range(15):
            add_recent_file(f"/book{i}.epub")
        recent = get_recent_files(max_items=10)
        self.assertLessEqual(len(recent), 10)


if __name__ == "__main__":
    unittest.main()
