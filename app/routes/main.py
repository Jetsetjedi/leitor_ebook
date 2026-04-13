"""Rota principal — biblioteca de livros."""
from flask import Blueprint, render_template, current_app, g
from app.models.database import get_db

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    db = get_db(current_app)
    books = db.execute(
        "SELECT id, title, author, format, file_size, added_at FROM books ORDER BY added_at DESC"
    ).fetchall()
    return render_template("index.html", books=books)
