"""FP046 Reading Intelligence regression tests."""
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


def test_percentage_progress_moves_want_to_read_to_reading(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    book = client.post("/api/reading/books", json={"title": "Test book"}).get_json()["book"]
    response = client.post(f"/api/reading/books/{book['id']}/progress", json={"value": 25, "unit": "percent"})
    assert response.status_code == 201
    updated = client.get(f"/api/reading/books/{book['id']}").get_json()["book"]
    assert updated["status"] == "reading"


def test_100_percent_marks_book_finished(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    book = client.post("/api/reading/books", json={"title": "Complete me"}).get_json()["book"]
    client.post(f"/api/reading/books/{book['id']}/progress", json={"value": 100, "unit": "percent"})
    updated = client.get(f"/api/reading/books/{book['id']}").get_json()["book"]
    assert updated["status"] == "finished"


def test_progress_history_returns_all_entries_newest_first(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    book = client.post("/api/reading/books", json={"title": "History"}).get_json()["book"]
    for value in (10, 30):
        assert client.post(f"/api/reading/books/{book['id']}/progress", json={"value": value, "unit": "percent"}).status_code == 201
    history = client.get(f"/api/reading/books/{book['id']}/progress").get_json()["progress"]
    assert [item["progress_value"] for item in history] == [30, 10]
