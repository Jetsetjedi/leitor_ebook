"""
Utilitários de upload e validação de arquivos.
Segurança: valida extensão, mimetype e usa nome gerado (evita path traversal).
"""
import os
import uuid
import magic  # python-magic
from pathlib import Path
from flask import current_app

MIME_WHITELIST = {
    "pdf":  ["application/pdf"],
    "epub": ["application/epub+zip", "application/zip"],
    "mobi": ["application/x-mobipocket-ebook", "application/octet-stream"],
    "txt":  ["text/plain"],
}


def allowed_extension(filename: str) -> bool:
    ext = _get_ext(filename)
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


def safe_save(file_storage) -> dict:
    """
    Valida e salva o arquivo enviado.
    Retorna dict com metadados ou lança ValueError em caso de arquivo inválido.
    
    Proteções:
    - Extensão na whitelist
    - MIME type real verificado via libmagic (não confia no header do browser)
    - Nome do arquivo no disco é UUID gerado — nunca o nome enviado pelo usuário
    """
    original_name = file_storage.filename or ""
    ext = _get_ext(original_name)

    if not ext or ext not in current_app.config["ALLOWED_EXTENSIONS"]:
        raise ValueError("Formato de arquivo não suportado.")

    # Lê os primeiros bytes para verificar o magic number
    header = file_storage.stream.read(2048)
    file_storage.stream.seek(0)

    detected_mime = magic.from_buffer(header, mime=True)
    if detected_mime not in MIME_WHITELIST.get(ext, []):
        raise ValueError(f"Conteúdo do arquivo não corresponde à extensão .{ext}.")

    safe_filename = f"{uuid.uuid4().hex}.{ext}"
    dest_path = Path(current_app.config["UPLOAD_FOLDER"]) / safe_filename
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    file_storage.save(str(dest_path))

    file_size = dest_path.stat().st_size
    title = Path(original_name).stem[:255]   # limita tamanho

    return {
        "original_name": original_name[:255],
        "filename": safe_filename,
        "format": ext,
        "title": title,
        "file_size": file_size,
    }


def _get_ext(filename: str) -> str:
    return Path(filename).suffix.lstrip(".").lower()
