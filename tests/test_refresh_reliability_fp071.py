"""FP071 tests: refresh reliability on slow hosts (Render free tier).

1. The isolated refresh child gets 240s (was 90s). The full pipeline takes
   ~34s on a phone but ~85-100s on Render, so 90s cut healthy refreshes off
   (13 Nov 2026: every refresh failed after two 90s attempts, 185s total).
2. A NewsData credential failure degrades to zero articles instead of
   killing the whole refresh. On 13 Nov 2026 the live refresh died every
   time with AttributeError at the NewsData stage because the deployed
   config/secrets.py did not define get_provider_key.
"""
from subprocess import CompletedProcess
from unittest.mock import Mock, patch

import main


def test_isolated_timeout_default_is_240_seconds():
    assert main.REFRESH_ISOLATED_TIMEOUT_SECONDS == 240
    payload = '[{"title":"Example","category":"World"}]'
    with patch.object(
        main.subprocess,
        "run",
        return_value=CompletedProcess(args=["python"], returncode=0, stdout=payload),
    ) as run:
        result = main._fetch_fresh_news_isolated()
    assert result == [{"title": "Example", "category": "World"}]
    assert run.call_args.kwargs["timeout"] == 240
    assert run.call_args.kwargs["timeout"] == main.REFRESH_ISOLATED_TIMEOUT_SECONDS


def test_isolated_timeout_override_still_applies():
    with patch.object(
        main.subprocess,
        "run",
        return_value=CompletedProcess(args=["python"], returncode=0, stdout="[]"),
    ) as run:
        assert main._fetch_fresh_news_isolated(timeout_seconds=30) == []
    assert run.call_args.kwargs["timeout"] == 30


def test_newsdata_key_lookup_attribute_error_returns_empty_list():
    # The exact 13 Nov 2026 live failure: the deployed secrets module had no
    # get_provider_key, so the lookup raised AttributeError and the refresh
    # child died. It must now degrade to zero articles.
    with patch.object(
        main.provider_secrets,
        "get_provider_key",
        side_effect=AttributeError("module has no attribute 'get_provider_key'"),
    ):
        with patch.object(main.requests, "get") as get:
            assert main.fetch_newsdata_articles() == []
            get.assert_not_called()


def test_newsdata_key_lookup_os_error_returns_empty_list():
    with patch.object(
        main.provider_secrets,
        "get_provider_key",
        side_effect=OSError("unreadable store"),
    ):
        with patch.object(main.requests, "get") as get:
            assert main.fetch_newsdata_articles() == []
            get.assert_not_called()


def test_newsdata_happy_path_unchanged_after_hardening():
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

    with patch.object(main.provider_secrets, "get_provider_key", return_value="test-key"):
        with patch.object(main.requests, "get", return_value=response) as get:
            articles = main.fetch_newsdata_articles()

    assert len(articles) == 1
    assert articles[0]["title"] == "Example football story"
    assert articles[0]["category"] == "Sport"
    assert articles[0]["source"] == "Example News"
    assert articles[0]["description"] == "Match report"
    assert articles[0]["feed_tier"] == "supplemental"
    assert get.call_args.kwargs["params"]["apikey"] == "test-key"
