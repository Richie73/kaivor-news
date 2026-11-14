"""FP081: reading and listening links in the Reading tab — BorrowBox,
Libby (OverDrive), Kindle and Audible. All four URLs were verified live
before building (14 Nov 2026)."""

from pathlib import Path

import pytest
from flask import Flask

from reading_web import reading_bp

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "reading.html"

LINKS = (
    ("BorrowBox", "https://www.borrowbox.com/"),
    ("Libby (OverDrive)", "https://libbyapp.com/"),
    ("Kindle", "https://read.amazon.co.uk/"),
    ("Audible", "https://www.audible.co.uk/"),
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("KAIVOR_READING_PIN", "test-pin-123")
    monkeypatch.setenv("KAIVOR_SESSION_SECRET", "test-session-secret-that-is-long-enough-123456")
    template_dir = Path(__file__).resolve().parents[1] / "templates"
    app = Flask(__name__, template_folder=str(template_dir))
    app.secret_key = "test-session-secret"
    app.config.update(TESTING=True, READING_DB_PATH=str(tmp_path / "reading.db"))
    app.register_blueprint(reading_bp)
    return app.test_client()


def unlock(client):
    response = client.post("/reading/login", data={"pin": "test-pin-123"})
    assert response.status_code == 302


def test_template_has_all_four_links():
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "Where I read &amp; listen" in text
    for label, url in LINKS:
        assert label in text
        assert f'href="{url}"' in text
        assert 'target="_blank"' in text
    assert "BorrowBox connection" not in text


def test_unlocked_reading_page_shows_links(client):
    unlock(client)
    response = client.get("/reading")
    assert response.status_code == 200
    for label, url in LINKS:
        assert label.encode() in response.data
        assert url.encode() in response.data


def test_locked_reading_page_hides_links(client):
    response = client.get("/reading")
    assert response.status_code == 200
    assert b"Unlock your reading library" in response.data
    for _, url in LINKS:
        assert url.encode() not in response.data
