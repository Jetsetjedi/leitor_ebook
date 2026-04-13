"""
Testes básicos — rode com: pytest
"""
import pytest
from app import create_app


@pytest.fixture()
def app():
    test_config = {
        "TESTING": True,
        "SECRET_KEY": "test-secret-key-do-not-use-in-production",
        "UPLOAD_FOLDER": "/tmp/leitor_ebook_test_uploads",
        "DATABASE_PATH": "/tmp/leitor_ebook_test.db",
    }
    application = create_app(test_config)
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


def test_index_returns_200(client):
    r = client.get("/")
    assert r.status_code == 200


def test_upload_no_file(client):
    r = client.post("/api/upload")
    assert r.status_code == 400


def test_upload_invalid_extension(client):
    from io import BytesIO
    data = {"file": (BytesIO(b"malware"), "virus.exe")}
    r = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert r.status_code in (400, 415)


def test_book_not_found(client):
    r = client.get("/reader/99999")
    assert r.status_code == 404


def test_api_progress_book_not_found(client):
    r = client.post("/api/book/99999/progress",
                    json={"position": 0},
                    content_type="application/json")
    assert r.status_code == 404
