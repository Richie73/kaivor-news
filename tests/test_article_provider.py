"""Provider attribution tests for article cards."""

import main


def test_newsdata_provider_label():
    assert main.article_provider_label({
        "feed_tier": "supplemental",
        "feed_url": "https://newsdata.io/api/1/latest",
    }) == "NewsData.io"


def test_guardian_provider_label():
    assert main.article_provider_label({
        "feed_tier": "primary",
        "feed_url": "https://content.guardianapis.com/search",
    }) == "The Guardian API"


def test_rss_provider_label():
    assert main.article_provider_label({
        "feed_tier": "primary",
        "feed_url": "https://feeds.bbci.co.uk/news/rss.xml",
    }) == "RSS"


def test_unknown_provider_is_not_guessed():
    assert main.article_provider_label({
        "feed_tier": "supplemental",
        "feed_url": "https://example.com/api",
    }) == "Other"
