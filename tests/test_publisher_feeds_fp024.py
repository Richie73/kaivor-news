"""FP024 regression tests for subscription-publisher RSS coverage."""

from news_freshness import build_feed_registry
from publisher_access import publisher_access_info, publisher_for_url


def _feeds_by_name(registry):
    return {
        feed["name"]: feed
        for feeds in registry.values()
        for feed in feeds
    }


def test_publishers_with_accessible_default_feeds_have_coverage():
    registry = build_feed_registry()
    feeds = _feeds_by_name(registry)

    expected = {
        "The New York Times",
        "The Independent",
        "The Athletic Football",
    }
    assert expected.issubset(feeds)
    # Telegraph's tested RSS endpoints return HTTP 402 in the deployment
    # environment, so do not advertise them as active feed coverage.
    assert "The Telegraph" not in feeds


def test_publisher_feeds_have_valid_https_urls_and_no_duplicate_urls():
    registry = build_feed_registry()
    publisher_names = {
        "The New York Times",
        "The Independent",
        "The Athletic Football",
    }
    publisher_feeds = [
        feed for feeds in registry.values() for feed in feeds
        if feed["name"] in publisher_names
    ]
    assert all(feed["url"].startswith("https://") for feed in publisher_feeds)
    for feeds in registry.values():
        urls = [feed["url"] for feed in feeds]
        assert len(urls) == len(set(urls))


def test_athletic_feed_is_classified_as_football_first():
    registry = build_feed_registry()
    athletic = next(
        feed
        for feed in registry["Sport"]
        if feed["name"] == "The Athletic Football"
    )
    assert athletic["sport_focus"] == "football"
    assert athletic["url"] == "https://theathletic.com/football/?rss=1"


def test_publisher_access_matches_the_four_supported_domains():
    cases = {
        "https://www.nytimes.com/2026/10/19/world/example.html": "The New York Times",
        "https://www.telegraph.co.uk/news/2026/10/19/example/": "The Telegraph",
        "https://www.independent.co.uk/news/uk/example.html": "The Independent",
        "https://theathletic.com/football/2026/10/19/example/": "The Athletic",
    }
    for url, expected in cases.items():
        info = publisher_access_info(url=url)
        assert info["supported"] is True
        assert info["publisher"] == expected


def test_nyt_hosted_athletic_rss_links_keep_athletic_label():
    info = publisher_for_url("https://www.nytimes.com/athletic/football/2026/10/19/example/")
    assert info is not None
    assert info["label"] == "The Athletic"


def test_unrelated_publishers_remain_unsupported():
    assert publisher_access_info(url="https://www.theguardian.com/world/2026/oct/19/example")["supported"] is False
