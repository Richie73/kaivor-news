"""FP039 regression tests for the dedicated Android news category."""

from news_freshness import build_feed_registry


def test_android_category_has_expected_publishers():
    registry = build_feed_registry()
    assert "Android" in registry
    by_name = {feed["name"]: feed for feed in registry["Android"]}
    expected = {"Android Police", "9to5Google", "Android Authority", "SamMobile", "Droid Life"}
    assert expected.issubset(by_name)
    assert all(feed["url"].startswith("https://") for feed in registry["Android"])


def test_android_feeds_are_deduplicated():
    registry = build_feed_registry()
    urls = [feed["url"] for feed in registry["Android"]]
    assert len(urls) == len(set(urls))


def test_android_category_does_not_replace_technology():
    registry = build_feed_registry()
    assert "Technology" in registry
    assert "Android" in registry
    assert any(feed["name"] == "TechCrunch" for feed in registry["Technology"])


def test_custom_android_feed_is_added_without_duplicate_defaults():
    custom_url = "https://example.com/android.xml"
    registry = build_feed_registry({"Android": [custom_url, custom_url]})
    matches = [feed for feed in registry["Android"] if feed["url"] == custom_url]
    assert len(matches) == 1
