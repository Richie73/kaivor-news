"""FP025 regression tests for per-feed diagnostics and safe API output."""
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import main
import news_freshness


def test_feed_diagnostics_distinguish_http_failure_from_empty_feed(monkeypatch):
    now = datetime.now(timezone.utc)
    failed = {"name": "HTTP Failure", "url": "https://example.com/fail", "tier": "custom"}
    empty = {"name": "Empty Feed", "url": "https://example.com/empty", "tier": "custom"}

    def fake_get(url, **kwargs):
        response = Mock()
        response.status_code = 503 if url.endswith("fail") else 200
        response.content = b"<rss><channel><title>Empty</title></channel></rss>"
        return response

    monkeypatch.setattr(news_freshness.requests, "get", fake_get)
    failed_diagnostic = {}
    assert news_freshness._fetch_feed(failed, "Test", now, 72, 15, failed_diagnostic) == []
    assert failed_diagnostic["status"] == "http_error"
    assert failed_diagnostic["error"] == "HTTP 503"
    diagnostic = {}
    assert news_freshness._fetch_feed(empty, "Test", now, 72, 15, diagnostic) == []
    assert diagnostic["status"] == "empty"
    assert diagnostic["article_count"] == 0
    assert diagnostic["error"] is None


def test_publisher_feed_endpoint_is_safe_and_reports_version(monkeypatch):
    with main._publisher_feed_lock:
        main._publisher_feed_state.update({
            "checked_at": 123.0,
            "snapshot": {"feed_count": 1, "status_counts": {"ok": 1}, "feeds": [{
                "publisher": "Example News", "category": "World", "status": "ok",
                "article_count": 3, "last_successful_at": "2026-10-22T00:00:00Z",
                "checked_at": "2026-10-22T00:00:00Z", "duration_ms": 42, "error": None,
            }]},
        })
    response = main.app.test_client().get("/api/publisher-feeds")
    assert response.status_code == 200
    data = response.get_json()
    assert data["version"] == "FP029.0"
    assert data["publisher_feeds"]["feeds"][0]["status"] == "ok"
    assert "feed_url" not in response.get_data(as_text=True)


def test_feed_fetch_exception_is_reported_without_exception_message(monkeypatch):
    feed = {"name": "Unavailable", "url": "https://example.com/rss", "tier": "custom"}
    def fail(*args, **kwargs):
        raise news_freshness.requests.Timeout("private transport detail")
    monkeypatch.setattr(news_freshness.requests, "get", fail)
    diagnostic = {}
    assert news_freshness._fetch_feed(feed, "World", datetime.now(timezone.utc), 72, 15, diagnostic) == []
    assert diagnostic["status"] == "request_error"
    assert diagnostic["error"] == "Timeout"
    assert "private transport detail" not in str(diagnostic)
