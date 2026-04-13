"""
API JSON — todas as operações de dados.
Proteções: rate limiting, validação de entrada, queries parametrizadas.
"""
import os
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app
from app.models.database import get_db
from app.utils.file_handler import safe_save, allowed_extension
from app.utils.book_processor import (
    extract_pdf_page, get_pdf_toc,
    extract_epub_chapter, get_epub_toc,
    extract_mobi_text,
    extract_txt_page,
    search_in_book,
)

api_bp = Blueprint("api", __name__)

# ─────────────────────────────────────────────────────────────────────────────
# Upload
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado."}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Nome de arquivo inválido."}), 400

    if not allowed_extension(file.filename):
        return jsonify({"error": "Formato não suportado."}), 415

    try:
        meta = safe_save(file)
    except ValueError as e:
        return jsonify({"error": str(e)}), 415

    db = get_db(current_app)
    try:
        db.execute(
            "INSERT INTO books (title, author, filename, format, file_size) VALUES (?, ?, ?, ?, ?)",
            (meta["title"], None, meta["filename"], meta["format"], meta["file_size"]),
        )
        db.commit()
        book_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    except Exception:
        # Remove arquivo caso o INSERT falhe
        dest = Path(current_app.config["UPLOAD_FOLDER"]) / meta["filename"]
        dest.unlink(missing_ok=True)
        return jsonify({"error": "Erro ao salvar livro no banco."}), 500

    return jsonify({"book_id": book_id, "title": meta["title"]}), 201


# ─────────────────────────────────────────────────────────────────────────────
# Conteúdo do livro
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/book/<int:book_id>/page/<int:page>", methods=["GET"])
def get_page(book_id: int, page: int):
    book, filepath = _get_book_or_404(book_id)
    fmt = book["format"]
    try:
        if fmt == "pdf":
            data = extract_pdf_page(filepath, page)
        elif fmt == "epub":
            data = extract_epub_chapter(filepath, page)
        elif fmt == "mobi":
            data = extract_mobi_text(filepath, page)
        elif fmt == "txt":
            data = extract_txt_page(filepath, page)
        else:
            return jsonify({"error": "Formato não suportado."}), 415
    except Exception as e:
        current_app.logger.error("Erro ao extrair página: %s", e)
        return jsonify({"error": "Não foi possível ler o arquivo."}), 500

    return jsonify(data)


@api_bp.route("/book/<int:book_id>/toc", methods=["GET"])
def get_toc(book_id: int):
    book, filepath = _get_book_or_404(book_id)
    fmt = book["format"]
    try:
        if fmt == "pdf":
            toc = get_pdf_toc(filepath)
        elif fmt == "epub":
            toc = get_epub_toc(filepath)
        else:
            toc = []
    except Exception as e:
        current_app.logger.error("Erro ao extrair TOC: %s", e)
        toc = []
    return jsonify(toc)


# ─────────────────────────────────────────────────────────────────────────────
# Progresso de leitura
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/book/<int:book_id>/progress", methods=["POST"])
def save_progress(book_id: int):
    _get_book_or_404(book_id)
    body = request.get_json(silent=True) or {}
    position = str(body.get("position", "0"))[:20]  # limita tamanho

    db = get_db(current_app)
    db.execute(
        """INSERT INTO reading_progress (book_id, position)
           VALUES (?, ?)
           ON CONFLICT(book_id) DO UPDATE SET position=excluded.position,
                                              updated_at=CURRENT_TIMESTAMP""",
        (book_id, position),
    )
    db.commit()
    return jsonify({"ok": True})


# ─────────────────────────────────────────────────────────────────────────────
# Marcadores
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/book/<int:book_id>/bookmarks", methods=["GET"])
def list_bookmarks(book_id: int):
    _get_book_or_404(book_id)
    db = get_db(current_app)
    rows = db.execute(
        "SELECT id, position, label, created_at FROM bookmarks WHERE book_id = ? ORDER BY created_at",
        (book_id,),
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@api_bp.route("/book/<int:book_id>/bookmarks", methods=["POST"])
def add_bookmark(book_id: int):
    _get_book_or_404(book_id)
    body = request.get_json(silent=True) or {}
    position = str(body.get("position", "0"))[:20]
    label = str(body.get("label", ""))[:200]

    db = get_db(current_app)
    db.execute(
        "INSERT INTO bookmarks (book_id, position, label) VALUES (?, ?, ?)",
        (book_id, position, label),
    )
    db.commit()
    bm_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    return jsonify({"id": bm_id}), 201


@api_bp.route("/book/<int:book_id>/bookmarks/<int:bm_id>", methods=["DELETE"])
def delete_bookmark(book_id: int, bm_id: int):
    db = get_db(current_app)
    db.execute(
        "DELETE FROM bookmarks WHERE id = ? AND book_id = ?", (bm_id, book_id)
    )
    db.commit()
    return jsonify({"ok": True})


# ─────────────────────────────────────────────────────────────────────────────
# Anotações
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/book/<int:book_id>/notes", methods=["GET"])
def list_notes(book_id: int):
    _get_book_or_404(book_id)
    db = get_db(current_app)
    rows = db.execute(
        "SELECT id, position, content, created_at FROM notes WHERE book_id = ? ORDER BY created_at",
        (book_id,),
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@api_bp.route("/book/<int:book_id>/notes", methods=["POST"])
def add_note(book_id: int):
    _get_book_or_404(book_id)
    body = request.get_json(silent=True) or {}
    position = str(body.get("position", "0"))[:20]
    content = str(body.get("content", ""))[:2000]  # limita tamanho da nota

    if not content.strip():
        return jsonify({"error": "Nota não pode ser vazia."}), 400

    db = get_db(current_app)
    db.execute(
        "INSERT INTO notes (book_id, position, content) VALUES (?, ?, ?)",
        (book_id, position, content),
    )
    db.commit()
    note_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    return jsonify({"id": note_id}), 201


@api_bp.route("/book/<int:book_id>/notes/<int:note_id>", methods=["DELETE"])
def delete_note(book_id: int, note_id: int):
    db = get_db(current_app)
    db.execute(
        "DELETE FROM notes WHERE id = ? AND book_id = ?", (note_id, book_id)
    )
    db.commit()
    return jsonify({"ok": True})


# ─────────────────────────────────────────────────────────────────────────────
# Busca
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/book/<int:book_id>/search", methods=["GET"])
def search(book_id: int):
    book, filepath = _get_book_or_404(book_id)
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])
    if len(query) > 200:
        return jsonify({"error": "Busca muito longa."}), 400

    results = search_in_book(filepath, book["format"], query)
    return jsonify(results)


# ─────────────────────────────────────────────────────────────────────────────
# Gerenciamento de livros
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/book/<int:book_id>/title", methods=["PATCH"])
def update_title(book_id: int):
    book, _ = _get_book_or_404(book_id)
    body = request.get_json(silent=True) or {}
    title = str(body.get("title", "")).strip()[:255]
    author = str(body.get("author", "")).strip()[:255]

    if not title:
        return jsonify({"error": "Título não pode ser vazio."}), 400

    db = get_db(current_app)
    db.execute(
        "UPDATE books SET title = ?, author = ? WHERE id = ?",
        (title, author or None, book_id),
    )
    db.commit()
    return jsonify({"ok": True})


@api_bp.route("/book/<int:book_id>", methods=["DELETE"])
def delete_book(book_id: int):
    book, filepath = _get_book_or_404(book_id)
    db = get_db(current_app)
    db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    # Remove arquivo do disco após confirmar exclusão no banco
    try:
        os.unlink(filepath)
    except OSError:
        pass
    return jsonify({"ok": True})


# ─────────────────────────────────────────────────────────────────────────────
# Helper interno
# ─────────────────────────────────────────────────────────────────────────────

def _get_book_or_404(book_id: int):
    db = get_db(current_app)
    book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if not book:
        from flask import abort
        abort(404)
    filepath = str(Path(current_app.config["UPLOAD_FOLDER"]) / book["filename"])
    return book, filepath
