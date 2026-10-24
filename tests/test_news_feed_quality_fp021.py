"""FP021.0 structural feed-quality and cache-safety regression tests."""
from unittest.mock import patch
import main
from news_feed_quality import assess_feed, article_rejection_reason, feed_quality_snapshot


def item(title="A real story", link="https://example.com/story", category="World", source="Example"):
    return {"title": title, "link": link, "category": category, "source": source}


def test_rejects_missing_title_and_invalid_link():
    assert article_rejection_reason(item(title="")) == "missing_title"
    assert article_rejection_reason(item(link="javascript:alert(1)")) == "invalid_link"


def test_assess_feed_deduplicates_and_counts_sources_categories():
    report = assess_feed([item(), item(), item("Another", "https://example.com/2", "Sport", "Wire")])
    assert report["input_count"] == 3
    assert report["accepted_count"] == 2
    assert report["duplicate_count"] == 1
    assert report["source_counts"] == {"Example": 1, "Wire": 1}
    assert report["category_counts"] == {"Sport": 1, "World": 1}


def test_assess_feed_rejects_non_objects_without_crashing():
    report = assess_feed([None, "bad", item()])
    assert report["accepted_count"] == 1
    assert report["rejected_count"] == 2


def test_snapshot_contains_only_aggregate_diagnostics():
    report = feed_quality_snapshot([item()])
    assert "articles" not in report
    assert report["accepted_count"] == 1


def test_refresh_preserves_cache_when_new_feed_is_invalid():
    old_articles = list(main._news_cache["articles"])
    old_updated = main._news_cache["last_updated"]
    try:
        with main._news_lock:
            main._news_cache["articles"] = [item()]
            main._news_cache["last_updated"] = 123.0
        result = main.refresh_news(fetcher=lambda: [{"title": "", "link": "#"}])
        assert result == []
        assert main._news_cache["articles"] == [item()]
        assert main._news_cache["last_updated"] == 123.0
    finally:
        with main._news_lock:
            main._news_cache["articles"] = old_articles
            main._news_cache["last_updated"] = old_updated


def test_quality_endpoint_reports_aggregate_counts_only():
    response = main.app.test_client().get("/api/news-quality")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["version"] == "FP030.0"
    assert "feed_quality" in payload
    assert "articles" not in payload["feed_quality"]
