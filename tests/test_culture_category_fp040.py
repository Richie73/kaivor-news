"""FP040 regression tests for the broad Culture news category."""
from pathlib import Path
from news_freshness import build_feed_registry


def test_culture_category_has_broad_verified_source_shortlist():
    registry = build_feed_registry()
    assert "Culture" in registry
    by_name = {feed["name"]: feed for feed in registry["Culture"]}
    expected = {
        "BBC Culture", "BBC Entertainment & Arts", "The Guardian Culture",
        "The Guardian Music", "Louder", "Kerrang!", "BFI", "France 24 Culture",
    }
    assert expected.issubset(by_name)
    assert all(feed["url"].startswith("https://") for feed in registry["Culture"])


def test_culture_feeds_are_unique():
    feeds = build_feed_registry()["Culture"]
    urls = [feed["url"] for feed in feeds]
    assert len(urls) == len(set(urls))


def test_culture_does_not_replace_existing_categories():
    registry = build_feed_registry()
    assert "Android" in registry and "Technology" in registry and "Culture" in registry
    assert any(feed["name"] == "Android Police" for feed in registry["Android"])
    assert any(feed["name"] == "TechCrunch" for feed in registry["Technology"])


def test_custom_culture_feed_is_added_without_duplicate_defaults():
    custom_url = "https://example.com/culture.xml"
    registry = build_feed_registry({"Culture": [custom_url, custom_url]})
    assert sum(feed["url"] == custom_url for feed in registry["Culture"]) == 1


def test_culture_is_in_refresh_pipeline_and_ui():
    main = Path("main.py").read_text(encoding="utf-8")
    template = Path("templates/index.html").read_text(encoding="utf-8")
    assert '"Culture": "culture"' in main
    assert 'for category in ("World", "Technology", "Android", "Culture", "Business", "Science", "UK", "Sport"):' in main
    assert "filterCategory('Culture',this)" in template
