from datetime import datetime, timedelta, timezone

from news_freshness import build_feed_registry, fetch_multi_source_news, parse_published
from news_store import normalise_article


def test_registry_has_broad_category_coverage():
    registry = build_feed_registry()
    assert set(["World", "Technology", "Business", "Science", "UK", "Sport"]).issubset(registry)
    assert len(registry["Technology"]) >= 5
    assert len(registry["World"]) >= 4
    assert len(registry["Sport"]) >= 4


def test_timestamp_parser():
    assert parse_published("2026-10-05T12:00:00Z") is not None
    assert parse_published("Mon, 05 Oct 2026 12:00:00 GMT") is not None


def test_freshness_filter_and_newest_first(monkeypatch):
    import news_freshness

    now = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)

    class FakeParsed:
        bozo = False
        feed = {"title": "Test Feed"}
        entries = [
            {"title": "Old", "link": "https://example.com/old", "published": "2026-10-01T12:00:00Z"},
            {"title": "Newest", "link": "https://example.com/new", "published": "2026-10-05T11:00:00Z"},
            {"title": "Middle", "link": "https://example.com/mid", "published": "2026-10-04T12:00:00Z"},
        ]

    monkeypatch.setattr(news_freshness.feedparser, "parse", lambda url, request_headers=None: FakeParsed())
    feed = {"name": "Test Feed", "url": "https://example.com/rss", "tier": "test"}
    result = news_freshness._fetch_feed(feed, "World", now, 72, 15)
    assert [item["title"] for item in result] == ["Newest", "Middle"]


def test_custom_sources_are_preserved():
    registry = build_feed_registry({"World": ["https://example.com/custom.xml"]})
    urls = [feed["url"] for feed in registry["World"]]
    assert "https://example.com/custom.xml" in urls


def test_sport_is_football_first():
    import news_freshness

    now = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
    class FakeParsed:
        bozo = False
        feed = {"title": "Sport Feed"}
        entries = [
            {"title": "NFL game latest", "link": "https://example.com/nfl", "published": "2026-10-05T11:59:00Z"},
            {"title": "Premier League transfer news", "link": "https://example.com/football", "published": "2026-10-05T11:00:00Z"},
        ]

    monkeypatch = __import__("pytest").MonkeyPatch()
    monkeypatch.setattr(news_freshness.feedparser, "parse", lambda url, request_headers=None: FakeParsed())
    general = {"name": "Test Sport", "url": "https://example.com/sport", "tier": "test"}
    football = {"name": "Test Football", "url": "https://example.com/football", "tier": "test", "sport_focus": "football"}
    other = news_freshness._fetch_feed(general, "Sport", now, 72, 15)
    focused = news_freshness._fetch_feed(football, "Sport", now, 72, 15)
    assert any(item["sport_focus"] == "football" for item in other)
    assert all(item["sport_focus"] == "football" for item in focused)
    monkeypatch.undo()


def test_sport_focus_survives_normalisation():
    item = normalise_article({
        "title": "Premier League update",
        "category": "Sport",
        "sport_focus": "football",
    })
    assert item["sport_focus"] == "football"
