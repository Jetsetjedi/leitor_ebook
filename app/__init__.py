"""
Leitor Ebook - Aplicação Flask principal
"""
import os
import secrets
from flask import Flask
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from .models.database import init_db


def create_app(config=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # ── Configuração base ──────────────────────────────────────────────────────
    app.config.from_object("app.config.Config")
    if config:
        app.config.update(config)

    # Garante que SECRET_KEY nunca é vazia
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = secrets.token_hex(32)

    # ── Segurança HTTP (HTTPS headers) ─────────────────────────────────────────
    csp = {
        "default-src": "'self'",
        "script-src": ["'self'", "'unsafe-inline'"],   # necessário para inline JS mínimo
        "style-src": ["'self'", "'unsafe-inline'"],
        "img-src": ["'self'", "data:", "blob:"],
        "font-src": "'self'",
        "object-src": "'none'",
        "frame-ancestors": "'none'",
    }
    Talisman(
        app,
        force_https=False,          # desabilita redirect HTTPS em dev local
        strict_transport_security=False,
        content_security_policy=csp,
        x_content_type_options=True,
        x_xss_protection=True,
        referrer_policy="strict-origin-when-cross-origin",
    )

    # ── Rate limiting ──────────────────────────────────────────────────────────
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per day", "60 per hour"],
        storage_uri="memory://",
    )
    app.extensions["limiter"] = limiter

    # ── Banco de dados ─────────────────────────────────────────────────────────
    init_db(app)

    # ── Blueprints ─────────────────────────────────────────────────────────────
    from .routes.main import main_bp
    from .routes.reader import reader_bp
    from .routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(reader_bp, url_prefix="/reader")
    app.register_blueprint(api_bp, url_prefix="/api")

    return app
