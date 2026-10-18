"""FP022 regression tests for cache safety and refresh lifecycle recovery."""
from unittest.mock import patch

import main


def _article(title="FP022 test story", link="https://example.com/fp022-story"):
    return {
        "title": title,
        "link": link,
        "category": "World",
        "source": "FP022 Test",
    }


def _save_news_state():
    with main._news_lock:
        cache = dict(main._news_cache)
        cache["articles"] = list(main._news_cache.get("articles") or [])
        quality = dict(main._feed_quality_state)
        quality["snapshot"] = dict(main._feed_quality_state.get("snapshot") or {})
        return cache, quality


def _restore_news_state(saved):
    cache, quality = saved
    with main._news_lock:
        main._news_cache.update(cache)
        main._feed_quality_state.update(quality)


def test_fetch_exception_preserves_cache_timestamp_and_quality_snapshot():
    saved = _save_news_state()
    existing = [_article("Existing cached story", "https://example.com/existing")]
    old_quality = {"accepted_count": 1, "rejected_count": 0, "source_counts": {"Existing": 1}}
    try:
        with main._news_lock:
            main._news_cache.update({"articles": existing, "last_updated": 1234.5})
            main._feed_quality_state.update({"checked_at": 1234.0, "snapshot": old_quality})

        def fail_fetch():
            raise TimeoutError("simulated provider timeout")

        try:
            main.refresh_news(fetcher=fail_fetch)
            assert False, "refresh_news should propagate the fetch failure to its worker"
        except TimeoutError:
            pass

        with main._news_lock:
            assert main._news_cache["articles"] == existing
            assert main._news_cache["last_updated"] == 1234.5
            assert main._feed_quality_state["checked_at"] == 1234.0
            assert main._feed_quality_state["snapshot"] == old_quality
    finally:
        _restore_news_state(saved)


def test_valid_refresh_replaces_cache_and_updates_quality_diagnostics():
    saved = _save_news_state()
    fresh = [
        _article("Fresh story one", "https://example.com/fresh-1"),
        _article("Fresh story two", "https://example.com/fresh-2"),
    ]
    try:
        with main._news_lock:
            main._news_cache.update({"articles": [_article()], "last_updated": 100.0})
        result = main.refresh_news(fetcher=lambda: fresh)
        assert result == fresh
        with main._news_lock:
            assert main._news_cache["articles"] == fresh
            assert main._news_cache["last_updated"] > 100.0
            assert main._feed_quality_state["snapshot"]["accepted_count"] == 2
            assert main._feed_quality_state["snapshot"]["rejected_count"] == 0
            assert main._feed_quality_state["checked_at"] > 0
    finally:
        _restore_news_state(saved)


def test_cron_refresh_endpoint_reports_already_running_without_starting_second_worker():
    old_state = dict(main._cron_refresh_state)
    old_token = main.os.environ.get("KAIVOR_CRON_TOKEN")
    try:
        main.os.environ["KAIVOR_CRON_TOKEN"] = "fp022-test-token"
        with main._cron_refresh_lock:
            main._cron_refresh_state.update({"running": True, "retry_after": 0.0})

        with patch.object(main.threading, "Thread") as thread:
            response = main.app.test_client().post(
                "/api/cron/refresh",
                headers={"Authorization": "Bearer fp022-test-token"},
            )
        assert response.status_code == 202
        assert response.get_json()["status"] == "already_running"
        thread.assert_not_called()
    finally:
        with main._cron_refresh_lock:
            main._cron_refresh_state.update(old_state)
        if old_token is None:
            main.os.environ.pop("KAIVOR_CRON_TOKEN", None)
        else:
            main.os.environ["KAIVOR_CRON_TOKEN"] = old_token


def test_expired_cooldown_allows_cron_refresh_to_start():
    old_state = dict(main._cron_refresh_state)
    old_token = main.os.environ.get("KAIVOR_CRON_TOKEN")
    try:
        main.os.environ["KAIVOR_CRON_TOKEN"] = "fp022-test-token"
        with main._cron_refresh_lock:
            main._cron_refresh_state.update({"running": False, "retry_after": main.time.time() - 1})

        with patch.object(main.threading, "Thread") as thread:
            response = main.app.test_client().post(
                "/api/cron/refresh",
                headers={"Authorization": "Bearer fp022-test-token"},
            )
        assert response.status_code == 202
        assert response.get_json()["status"] == "started"
        thread.assert_called_once()
        thread.return_value.start.assert_called_once()
    finally:
        with main._cron_refresh_lock:
            main._cron_refresh_state.update(old_state)
        if old_token is None:
            main.os.environ.pop("KAIVOR_CRON_TOKEN", None)
        else:
            main.os.environ["KAIVOR_CRON_TOKEN"] = old_token
