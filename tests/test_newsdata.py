"""NewsData.io provider regression tests."""

from unittest.mock import Mock, patch

import main


def test_missing_api_key_returns_empty_list():
    with patch.dict(main.os.environ, {"NEWSDATA_API_KEY": ""}, clear=False):
        with patch.object(main.requests, "get") as get:
            assert main.fetch_newsdata_articles() == []
            get.assert_not_called()


def test_successful_response_maps_articles_and_limits_categories():
    payload = {
        "results": [
            {
                "title": "Example football story",
                "description": "<b>Match</b> report",
                "link": "https://example.com/story",
                "category": ["sports"],
                "source_name": "Example News",
                "pubDate": "2026-10-11 10:00:00",
            }
        ]
    }
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload

    with patch.dict(main.os.environ, {"NEWSDATA_API_KEY": "test-key"}):
        with patch.object(main.requests, "get", return_value=response) as get:
            articles = main.fetch_newsdata_articles()

    assert len(articles) == 1
    assert articles[0]["title"] == "Example football story"
    assert articles[0]["category"] == "Sport"
    assert articles[0]["source"] == "Example News"
    assert articles[0]["description"] == "Match report"
    assert articles[0]["feed_tier"] == "supplemental"
    assert articles[0]["link"] == "https://example.com/story"

    params = get.call_args.kwargs["params"]
    assert params["category"] == "world,technology,business,science,sports"
    assert len(params["category"].split(",")) == 5
    assert params["apikey"] == "test-key"


def test_invalid_articles_are_skipped():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "results": [
            {"title": "Missing link"},
            {"title": "", "link": "https://example.com/empty"},
            {"title": "Bad link", "link": "javascript:alert(1)"},
            None,
            {
                "title": "Valid story",
                "link": "https://example.com/valid",
                "category": ["world"],
            },
        ]
    }

    with patch.dict(main.os.environ, {"NEWSDATA_API_KEY": "test-key"}):
        with patch.object(main.requests, "get", return_value=response):
            articles = main.fetch_newsdata_articles()

    assert len(articles) == 1
    assert articles[0]["title"] == "Valid story"
    assert articles[0]["category"] == "World"


def test_api_failure_returns_empty_list():
    with patch.dict(main.os.environ, {"NEWSDATA_API_KEY": "test-key"}):
        with patch.object(
            main.requests,
            "get",
            side_effect=main.requests.RequestException("simulated failure"),
        ):
            assert main.fetch_newsdata_articles() == []


def test_articles_with_missing_or_unsupported_category_are_skipped():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "results": [
            {
                "title": "Uncategorised story",
                "link": "https://example.com/uncategorised",
                "category": [],
            },
            {
                "title": "Unexpected category story",
                "link": "https://example.com/unexpected",
                "category": ["lifestyle"],
            },
            {
                "title": "Valid business story",
                "link": "https://example.com/business",
                "category": ["business"],
            },
        ]
    }

    with patch.dict(main.os.environ, {"NEWSDATA_API_KEY": "test-key"}):
        with patch.object(main.requests, "get", return_value=response):
            articles = main.fetch_newsdata_articles()

    assert len(articles) == 1
    assert articles[0]["title"] == "Valid business story"
    assert articles[0]["category"] == "Business"
