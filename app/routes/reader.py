"""Rota do leitor — renderiza o ebook no browser."""
from flask import Blueprint, render_template, abort, current_app
from app.models.database import get_db

reader_bp = Blueprint("reader", __name__)


@reader_bp.route("/<int:book_id>")
def read(book_id: int):
    db = get_db(current_app)
    book = db.execute(
        "SELECT * FROM books WHERE id = ?", (book_id,)
    ).fetchone()
    if not book:
        abort(404)

    progress = db.execute(
        "SELECT position FROM reading_progress WHERE book_id = ?", (book_id,)
    ).fetchone()

    start_position = int(progress["position"]) if progress else 0

    return render_template(
        "reader.html",
        book=book,
        start_position=start_position,
    )
