"""
Configurações da aplicação — separadas por ambiente.
Nunca exponha SECRET_KEY ou credenciais no código-fonte!
Use variáveis de ambiente ou um arquivo .env (não commitar).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    # ── Segurança ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = os.environ.get("SECRET_KEY") or ""
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    SESSION_COOKIE_SECURE: bool = os.environ.get("FLASK_ENV") == "production"
    PERMANENT_SESSION_LIFETIME: int = 3600  # 1 hora

    # ── Upload de arquivos ─────────────────────────────────────────────────────
    UPLOAD_FOLDER: str = str(BASE_DIR / "uploads")
    MAX_CONTENT_LENGTH: int = 50 * 1024 * 1024   # 50 MB máximo
    ALLOWED_EXTENSIONS: set = {"pdf", "epub", "mobi", "txt"}

    # ── Banco de dados ─────────────────────────────────────────────────────────
    DATABASE_PATH: str = str(BASE_DIR / "data" / "library.db")

    # ── Aplicação ──────────────────────────────────────────────────────────────
    DEBUG: bool = False
    TESTING: bool = False


class DevelopmentConfig(Config):
    DEBUG: bool = True


class ProductionConfig(Config):
    SESSION_COOKIE_SECURE: bool = True
    DEBUG: bool = False
