"""Bookmarks persistence module."""

import json
import os
from dataclasses import asdict, dataclass
from typing import Dict, List


@dataclass
class Bookmark:
    """Represents a reading position bookmark."""

    file_path: str
    position: int  # chapter index (EPUB) or page number (PDF)
    label: str


_BOOKMARKS_FILE = os.path.join(
    os.path.expanduser("~"), ".leitor_ebook_bookmarks.json"
)


def _load_data() -> Dict:
    if os.path.exists(_BOOKMARKS_FILE):
        try:
            with open(_BOOKMARKS_FILE, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            pass
    return {"bookmarks": [], "recent_files": []}


def _save_data(data: Dict) -> None:
    with open(_BOOKMARKS_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def get_bookmarks(file_path: str) -> List[Bookmark]:
    """Return all bookmarks for a specific file."""
    data = _load_data()
    return [
        Bookmark(**bm)
        for bm in data["bookmarks"]
        if bm["file_path"] == file_path
    ]


def add_bookmark(bookmark: Bookmark) -> None:
    """Persist a new bookmark."""
    data = _load_data()
    # Avoid exact duplicates
    for existing in data["bookmarks"]:
        if (
            existing["file_path"] == bookmark.file_path
            and existing["position"] == bookmark.position
        ):
            return
    data["bookmarks"].append(asdict(bookmark))
    _save_data(data)


def remove_bookmark(file_path: str, position: int) -> None:
    """Remove a bookmark by file path and position."""
    data = _load_data()
    data["bookmarks"] = [
        bm
        for bm in data["bookmarks"]
        if not (bm["file_path"] == file_path and bm["position"] == position)
    ]
    _save_data(data)


def get_recent_files(max_items: int = 10) -> List[str]:
    """Return a list of recently opened file paths."""
    data = _load_data()
    return data.get("recent_files", [])[:max_items]


def add_recent_file(file_path: str, max_items: int = 10) -> None:
    """Add a file to the recent files list."""
    data = _load_data()
    recent = data.get("recent_files", [])
    if file_path in recent:
        recent.remove(file_path)
    recent.insert(0, file_path)
    data["recent_files"] = recent[:max_items]
    _save_data(data)
