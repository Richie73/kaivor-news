"""Tests for the private Kaivor News Reading interface (FP042)."""
from pathlib import Path

import pytest
from flask import Flask

from reading_web import reading_bp


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("KAIVOR_READING_PIN", "test-pin-123")
    monkeypatch.setenv("KAIVOR_SESSION_SECRET", "test-session-secret-that-is-long-enough-123456")
    # The test module lives under tests/, so Flask's default relative
    # template lookup would incorrectly search tests/templates. Point the
    # test app at the project's real templates directory, as main.py does.
    template_dir = Path(__file__).resolve().parents[1] / "templates"
    app = Flask(__name__, template_folder=str(template_dir))
    app.secret_key = "test-session-secret"
    app.config.update(TESTING=True, READING_DB_PATH=str(tmp_path / "reading.db"))
    app.register_blueprint(reading_bp)
    return app.test_client()


def unlock(client):
    response = client.post("/reading/login", data={"pin": "test-pin-123"})
    assert response.status_code == 302


def test_reading_page_is_locked_before_login(client):
    response = client.get("/reading")
    assert response.status_code == 200
    assert b"Unlock your reading library" in response.data
    assert client.get("/api/reading/dashboard").status_code == 401


def test_wrong_pin_does_not_unlock(client):
    client.post("/reading/login", data={"pin": "wrong-pin"})
    assert client.get("/api/reading/dashboard").status_code == 401


def test_dashboard_and_book_crud(client):
    unlock(client)
    response = client.post("/api/reading/books", json={
        "title": "Dune", "author": "Frank Herbert", "book_format": "ebook"
    })
    assert response.status_code == 201
    book = response.get_json()["book"]
    book_id = book["id"]

    dashboard = client.get("/api/reading/dashboard").get_json()
    assert dashboard["summary"]["total"] == 1
    assert dashboard["books"][0]["book"]["title"] == "Dune"

    updated = client.patch(f"/api/reading/books/{book_id}", json={"status": "reading"})
    assert updated.status_code == 200
    assert updated.get_json()["book"]["status"] == "reading"

    deleted = client.delete(f"/api/reading/books/{book_id}")
    assert deleted.status_code == 200
    assert client.get("/api/reading/books/999").status_code == 404


def test_notes_progress_and_lists(client):
    unlock(client)
    book = client.post("/api/reading/books", json={"title": "Atomic Habits"}).get_json()["book"]
    book_id = book["id"]

    note = client.post(f"/api/reading/books/{book_id}/notes", json={
        "note": "Make it obvious", "page_reference": "Chapter 1"
    })
    assert note.status_code == 201
    assert client.get(f"/api/reading/books/{book_id}/notes").get_json()["notes"][0]["note"] == "Make it obvious"

    progress = client.post(f"/api/reading/books/{book_id}/progress", json={"value": 35, "unit": "percent"})
    assert progress.status_code == 201
    assert progress.get_json()["progress"]["progress_value"] == 35

    reading_list = client.post("/api/reading/lists", json={"name": "Weekend reading"}).get_json()["list"]
    add = client.post(f"/api/reading/lists/{reading_list['id']}/books", json={"book_id": book_id})
    assert add.status_code == 200
    assert len(client.get(f"/api/reading/lists/{reading_list['id']}/books").get_json()["books"]) == 1


def test_borrowbox_provider_is_visible_but_not_connected(client):
    unlock(client)
    data = client.get("/api/reading/providers").get_json()
    provider = data["providers"][0]
    assert provider["name"] == "borrowbox"
    assert provider["connected"] is False
    assert provider["launch_url"] == "https://www.borrowbox.com/"
    assert provider["capabilities"]["loans"] is False


def test_unconfigured_pin_disables_api(client, monkeypatch):
    monkeypatch.delenv("KAIVOR_READING_PIN")
    response = client.get("/api/reading/dashboard")
    assert response.status_code == 503
