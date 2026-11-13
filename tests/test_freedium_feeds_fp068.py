"""FP068 regression tests for the Freedium publishers' feeds in the registry."""
from news_freshness import build_feed_registry

# (category, feed name, URL, tier) — the 13 feeds FP068 adds to DEFAULT_FEEDS.
NEW_FEEDS = [
    ("World", "The Washington Post", "https://feeds.washingtonpost.com/rss/world", "major"),
    ("World", "Financial Times", "https://www.ft.com/world?format=rss", "major"),
    ("World", "The Economist", "https://www.economist.com/international/rss.xml", "major"),
    ("Technology", "The Washington Post", "https://feeds.washingtonpost.com/rss/business/technology", "major"),
    ("Technology", "Financial Times", "https://www.ft.com/technology?format=rss", "major"),
    ("Technology", "Bloomberg", "https://www.bloomberg.com/feeds/technology/news.rss", "specialist"),
    ("Business", "Bloomberg", "https://www.bloomberg.com/feeds/markets/news.rss", "major"),
    ("Business", "The Washington Post", "https://feeds.washingtonpost.com/rss/business", "major"),
    ("Business", "Financial Times", "https://www.ft.com/companies?format=rss", "major"),
    ("Business", "The Economist", "https://www.economist.com/finance-and-economics/rss.xml", "major"),
    ("Science", "The New York Times", "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml", "primary"),
    ("Science", "The Economist", "https://www.economist.com/science-and-technology/rss.xml", "major"),
    ("UK", "The Economist", "https://www.economist.com/britain/rss.xml", "major"),
]


def test_freedium_feeds_present_in_matching_categories():
    registry = build_feed_registry()
    for category, name, url, tier in NEW_FEEDS:
        matches = [feed for feed in registry[category] if feed["url"] == url]
        assert len(matches) == 1, f"{url} missing or duplicated in {category}"
        assert matches[0]["name"] == name
        assert matches[0]["tier"] == tier


def test_freedium_feeds_are_https():
    for _, _, url, _ in NEW_FEEDS:
        assert url.startswith("https://")


def test_registry_has_no_duplicate_urls():
    registry = build_feed_registry()
    urls = [feed["url"] for feeds in registry.values() for feed in feeds]
    assert len(urls) == len(set(urls))


def test_category_and_total_counts():
    registry = build_feed_registry()
    assert len(registry["World"]) == 9
    assert len(registry["Technology"]) == 10
    assert len(registry["Business"]) == 10
    assert len(registry["Science"]) == 6
    assert len(registry["UK"]) == 5
    assert sum(len(feeds) for feeds in registry.values()) == 61


def test_existing_categories_untouched():
    registry = build_feed_registry()
    assert len(registry["Android"]) == 5
    assert len(registry["Culture"]) == 8
    assert len(registry["Sport"]) == 8
    assert any(feed["name"] == "Android Police" for feed in registry["Android"])
    assert any(feed["name"] == "BBC Sport Football" for feed in registry["Sport"])


def test_reuters_and_medium_have_no_registry_feed():
    # Reuters has no working public RSS feed; Medium has no editorial feed.
    # Both stay covered by the extractor fallback for links from other sources.
    registry = build_feed_registry()
    urls = [feed["url"] for feeds in registry.values() for feed in feeds]
    assert not any("reuters.com" in url for url in urls)
    assert not any("medium.com" in url for url in urls)


def test_custom_sources_still_merge_without_duplicates():
    custom_url = "https://example.com/world.xml"
    registry = build_feed_registry({"World": [custom_url, custom_url]})
    assert sum(feed["url"] == custom_url for feed in registry["World"]) == 1
