"""FP018.7 regression tests for safe news-cache refreshes."""

from unittest.mock import patch

import main


def test_empty_refresh_preserves_existing_news():
    existing_article = {
        "id": "existing-story",
        "title": "Existing story",
        "category": "World",
    }

    with main._news_lock:
        original_articles = list(main._news_cache["articles"])
        original_updated = main._news_cache["last_updated"]
        main._news_cache["articles"] = [existing_article]
        main._news_cache["last_updated"] = 12345.0

    try:
        with patch.object(main, "fetch_fresh_news", return_value=[]):
            result = main.refresh_news()

        assert result == []
        with main._news_lock:
            assert main._news_cache["articles"] == [existing_article]
            assert main._news_cache["last_updated"] == 12345.0
    finally:
        with main._news_lock:
            main._news_cache["articles"] = original_articles
            main._news_cache["last_updated"] = original_updated



def test_cold_start_recovery_starts_once():
    with main._news_lock:
        old_articles = main._news_cache["articles"]
        main._news_cache["articles"] = []
    with main._cron_refresh_lock:
        old_state = dict(main._cron_refresh_state)
        main._cron_refresh_state["running"] = False

    try:
        with patch.object(main.threading, "Thread") as thread:
            assert main._ensure_news_refresh_started() is True
            assert main._ensure_news_refresh_started() is False
            thread.assert_called_once()
            thread.return_value.start.assert_called_once()
    finally:
        with main._news_lock:
            main._news_cache["articles"] = old_articles
        with main._cron_refresh_lock:
            main._cron_refresh_state.update(old_state)


def test_cold_start_recovery_skips_populated_cache():
    with main._news_lock:
        old_articles = main._news_cache["articles"]
        main._news_cache["articles"] = [{"id": "existing-story"}]
    with main._cron_refresh_lock:
        old_state = dict(main._cron_refresh_state)
        main._cron_refresh_state["running"] = False

    try:
        with patch.object(main.threading, "Thread") as thread:
            assert main._ensure_news_refresh_started() is False
            thread.assert_not_called()
    finally:
        with main._news_lock:
            main._news_cache["articles"] = old_articles
        with main._cron_refresh_lock:
            main._cron_refresh_state.update(old_state)


def test_cold_start_recovery_skips_existing_refresh():
    with main._news_lock:
        old_articles = main._news_cache["articles"]
        main._news_cache["articles"] = []
    with main._cron_refresh_lock:
        old_state = dict(main._cron_refresh_state)
        main._cron_refresh_state["running"] = True

    try:
        with patch.object(main.threading, "Thread") as thread:
            assert main._ensure_news_refresh_started() is False
            thread.assert_not_called()
    finally:
        with main._news_lock:
            main._news_cache["articles"] = old_articles
        with main._cron_refresh_lock:
            main._cron_refresh_state.update(old_state)
