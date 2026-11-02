"""FP047 Reading dashboard performance and form reliability regressions."""
from pathlib import Path

from flask import Flask

from reading_web import reading_bp


def make_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KAIVOR_READING_PIN", "test-pin-123")
    monkeypatch.setenv("KAIVOR_SESSION_SECRET", "test-session-secret-that-is-long-enough-123456")
    app = Flask(__name__, template_folder=str(Path(__file__).resolve().parents[1] / "templates"))
    app.secret_key = "test-session-secret"
    app.config.update(TESTING=True, READING_DB_PATH=str(tmp_path / "reading.db"))
    app.register_blueprint(reading_bp)
    client = app.test_client()
    client.post("/reading/login", data={"pin": "test-pin-123"})
    return client


def test_dashboard_snapshot_includes_latest_progress_notes_and_lists(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    book = client.post("/api/reading/books", json={"title": "Dashboard snapshot"}).get_json()["book"]
    book_id = book["id"]
    client.post(f"/api/reading/books/{book_id}/notes", json={"note": "Snapshot note"})
    client.post(f"/api/reading/books/{book_id}/progress", json={"value": 42, "unit": "percent"})
    reading_list = client.post("/api/reading/lists", json={"name": "FP047 list"}).get_json()["list"]
    client.post(f"/api/reading/lists/{reading_list['id']}/books", json={"book_id": book_id})

    response = client.get("/api/reading/dashboard")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["summary"]["total"] == 1
    assert payload["summary"]["notes"] == 1
    assert payload["books"][0]["book"]["id"] == book_id
    assert payload["books"][0]["progress"]["progress_value"] == 42
    assert payload["books"][0]["notes_count"] == 1
    assert payload["lists"][0]["name"] == "FP047 list"
    assert payload["lists"][0]["book_count"] == 1


def test_reading_template_captures_form_before_async_reset():
    template = (Path(__file__).resolve().parents[1] / "templates" / "reading.html").read_text()
    assert "const formElement = event.currentTarget" in template
    assert "formElement.reset()" in template
    assert "event.currentTarget.reset()" not in template


def test_reading_search_filters_cached_books_without_dashboard_requests():
    template = (Path(__file__).resolve().parents[1] / "templates" / "reading.html").read_text()
    assert "$('search-books').addEventListener('input',applyBookFilters)" in template
    assert "$('filter-status').addEventListener('change',applyBookFilters)" in template
    assert "loadListsAndBooks" not in template
