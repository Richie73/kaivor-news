"""FP105: Readwise highlights in the Reading tab.

Kaivor pulls highlights read-only via the Readwise export API
(GET /api/v2/export/, Token auth, pageCursor paging), stores the
newest 500, and shows them in a sidebar panel on /reading with a
Sync button. The GET route needs the unlocked session (highlights
are private, like the calendar); the sync POST is PIN-gated and
needs KAIVOR_READWISE_TOKEN from readwise.io/access_token.
"""
from pathlib import Path
from unittest.mock import patch

import requests

import main
import news_store
import readwise_client
from readwise_client import (
    ReadwiseError,
    fetch_all_highlights,
    fetch_export_page,
    flatten_export,
    sync_highlights,
)

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "reading.html"


def highlight(**overrides):
    item = {
        "id": 1,
        "text": "Call me Ishmael.",
        "note": None,
        "color": "yellow",
        "highlighted_at": "2026-11-01T10:00:00Z",
        "updated_at": "2026-11-02T10:00:00Z",
        "readwise_url": "https://readwise.io/open/1",
        "tags": [],
        "is_favorite": False,
        "is_deleted": False,
        "is_discard": False,
    }
    item.update(overrides)
    return item


def book(**overrides):
    item = {
        "user_book_id": 123,
        "is_deleted": False,
        "title": "Moby Dick",
        "author": "Herman Melville",
        "category": "books",
        "highlights": [],
    }
    item.update(overrides)
    return item


PAGE_1 = {
    "count": 2,
    "nextPageCursor": "cursor-2",
    "results": [
        book(
            highlights=[
                highlight(id=1, note="Opening line"),
                highlight(id=2, text="Deleted highlight", is_deleted=True),
                highlight(id=3, text="Discarded highlight", is_discard=True),
                highlight(id=4, text="   "),
            ]
        ),
        book(
            user_book_id=124,
            is_deleted=True,
            title="Deleted book",
            highlights=[highlight(id=5, text="Should not appear")],
        ),
    ],
}

PAGE_2 = {
    "count": 1,
    "nextPageCursor": None,
    "results": [
        book(
            user_book_id=125,
            title="The Hobbit",
            author="J. R. R. Tolkien",
            highlights=[
                highlight(
                    id=6,
                    text="In a hole in the ground there lived a hobbit.",
                    updated_at="2026-11-05T10:00:00Z",
                )
            ],
        )
    ],
}


class FakeResponse:
    def __init__(self, payload=None, status_code=200, bad_json=False):
        self._payload = payload or {}
        self.status_code = status_code
        self._bad_json = bad_json

    def json(self):
        if self._bad_json:
            raise ValueError("not json")
        return self._payload


# --- flatten ---

def test_flatten_export_skips_deleted_and_empty():
    highlights = flatten_export(PAGE_1["results"])
    assert len(highlights) == 1
    kept = highlights[0]
    assert kept["id"] == 1
    assert kept["text"] == "Call me Ishmael."
    assert kept["note"] == "Opening line"
    assert kept["title"] == "Moby Dick"
    assert kept["author"] == "Herman Melville"
    assert kept["category"] == "books"
    assert kept["readwise_url"] == "https://readwise.io/open/1"


def test_flatten_export_sorts_newest_first():
    old = highlight(id=10, text="Old", updated_at="2026-01-01T00:00:00Z")
    new = highlight(id=11, text="New", updated_at="2026-11-01T00:00:00Z")
    highlights = flatten_export([book(highlights=[old, new])])
    assert [h["id"] for h in highlights] == [11, 10]


# --- paging ---

def test_fetch_all_highlights_follows_pagination():
    calls = []

    def fake_get(url, headers=None, params=None, timeout=None):
        calls.append(params or {})
        if params and params.get("pageCursor") == "cursor-2":
            return FakeResponse(PAGE_2)
        return FakeResponse(PAGE_1)

    with patch.object(readwise_client.requests, "get", side_effect=fake_get):
        highlights, complete = fetch_all_highlights("token")
    assert complete is True
    assert [h["id"] for h in highlights] == [6, 1]
    assert calls[0] == {}
    assert calls[1] == {"pageCursor": "cursor-2"}


def test_fetch_all_highlights_page_cap():
    endless = {"count": 1, "nextPageCursor": "more", "results": []}
    with patch.object(
        readwise_client.requests, "get", return_value=FakeResponse(endless)
    ) as get:
        _highlights, complete = fetch_all_highlights("token", max_pages=2)
    assert complete is False
    assert get.call_count == 2


def test_fetch_export_page_errors():
    with patch.object(
        readwise_client.requests, "get", return_value=FakeResponse({}, status_code=401)
    ):
        try:
            fetch_export_page("bad-token")
        except ReadwiseError as exc:
            assert "refused" in str(exc)
        else:
            raise AssertionError("401 must raise")
    with patch.object(
        readwise_client.requests, "get", return_value=FakeResponse({}, status_code=500)
    ):
        try:
            fetch_export_page("token")
        except ReadwiseError as exc:
            assert "500" in str(exc)
        else:
            raise AssertionError("500 must raise")
    with patch.object(
        readwise_client.requests, "get", side_effect=requests.RequestException("down")
    ):
        try:
            fetch_export_page("token")
        except ReadwiseError:
            pass
        else:
            raise AssertionError("network failure must raise")
    with patch.object(
        readwise_client.requests, "get", return_value=FakeResponse(bad_json=True)
    ):
        try:
            fetch_export_page("token")
        except ReadwiseError:
            pass
        else:
            raise AssertionError("bad JSON must raise")


def test_sync_highlights_caps_at_500():
    many = [highlight(id=n, text=f"Highlight {n}") for n in range(600)]
    with patch.object(readwise_client, "fetch_all_highlights", return_value=(many, True)):
        payload = sync_highlights("token")
    assert len(payload["highlights"]) == 500
    assert payload["total"] == 600
    assert payload["complete"] is True
    assert payload["last_sync"] > 0


# --- store ---

def test_readwise_store_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(news_store, "READWISE_FILE", tmp_path / "readwise.json")
    assert news_store.load_readwise_highlights() == {
        "highlights": [],
        "last_sync": 0,
        "total": 0,
        "complete": True,
    }
    payload = {"highlights": [{"id": 1, "text": "Hi"}], "last_sync": 123, "total": 1, "complete": True}
    assert news_store.save_readwise_highlights(payload) == payload
    assert news_store.load_readwise_highlights() == payload


# --- routes ---

def test_highlights_route_is_pin_gated(authed_client):
    client = main.app.test_client()
    response = client.get("/api/reading/highlights")
    assert response.status_code in {401, 503}
    stored = {"highlights": [{"id": 1, "text": "Hi"}], "last_sync": 123, "total": 1, "complete": True}
    with patch.object(main, "load_readwise_highlights", return_value=stored):
        response = authed_client.get("/api/reading/highlights")
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["highlights"] == stored["highlights"]


def test_sync_route_is_guarded():
    client = main.app.test_client()
    response = client.post("/api/reading/highlights/sync")
    assert response.status_code in {401, 503}


def test_sync_route_round_trip(authed_client, monkeypatch):
    monkeypatch.setenv("KAIVOR_READWISE_TOKEN", "fp105-test-token")
    payload = {"highlights": [{"id": 1, "text": "Hi"}], "last_sync": 123, "total": 1, "complete": True}
    with (
        patch.object(main, "sync_highlights", return_value=payload) as sync,
        patch.object(main, "save_readwise_highlights", return_value=payload),
    ):
        response = authed_client.post("/api/reading/highlights/sync")
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["count"] == 1
    assert body["total"] == 1
    sync.assert_called_once_with("fp105-test-token")


def test_sync_route_requires_token(authed_client, monkeypatch):
    monkeypatch.delenv("KAIVOR_READWISE_TOKEN", raising=False)
    response = authed_client.post("/api/reading/highlights/sync")
    assert response.status_code == 503
    assert "KAIVOR_READWISE_TOKEN" in response.get_json()["error"]


def test_sync_route_readwise_failure_is_502(authed_client, monkeypatch):
    monkeypatch.setenv("KAIVOR_READWISE_TOKEN", "fp105-test-token")
    with patch.object(main, "sync_highlights", side_effect=ReadwiseError("Readwise refused the access token.")):
        response = authed_client.post("/api/reading/highlights/sync")
    assert response.status_code == 502
    assert "refused" in response.get_json()["error"]


# --- template ---

def test_highlights_panel_in_reading_template():
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "Readwise highlights" in text
    assert 'id="highlights-list"' in text
    assert 'id="sync-highlights-btn"' in text
    assert 'id="highlights-status"' in text
    assert "loadReadwiseHighlights();" in text
    assert "/api/reading/highlights" in text
    assert "/api/reading/highlights/sync" in text
