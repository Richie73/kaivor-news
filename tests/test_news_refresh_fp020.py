"""FP020 regression tests for bounded refresh retries and cooldown recovery."""

from unittest.mock import patch

import main


def _save_refresh_state():
    with main._cron_refresh_lock:
        return dict(main._cron_refresh_state)


def _restore_refresh_state(state):
    with main._cron_refresh_lock:
        main._cron_refresh_state.update(state)


def test_worker_retries_once_then_records_success():
    old_state = _save_refresh_state()
    try:
        with main._cron_refresh_lock:
            main._cron_refresh_state.update({
                "running": True,
                "started_at": 1000.0,
                "last_attempt_count": 0,
                "consecutive_failures": 2,
                "retry_after": 9999999999.0,
            })

        with patch.object(
            main,
            "refresh_news",
            side_effect=[RuntimeError("temporary failure"), [{"title": "Recovered"}]],
        ) as refresh, patch.object(main.time, "sleep") as sleep:
            main._cron_refresh_worker()

        assert refresh.call_count == 2
        sleep.assert_called_once_with(main.REFRESH_RETRY_BACKOFF_SECONDS)
        with main._cron_refresh_lock:
            state = dict(main._cron_refresh_state)
        assert state["running"] is False
        assert state["last_successful"] > 0
        assert state["last_count"] == 1
        assert state["last_error"] == ""
        assert state["last_attempt_count"] == 2
        assert state["consecutive_failures"] == 0
        assert state["retry_after"] == 0.0
    finally:
        _restore_refresh_state(old_state)


def test_worker_sets_cooldown_after_bounded_retries_fail():
    old_state = _save_refresh_state()
    try:
        with main._cron_refresh_lock:
            main._cron_refresh_state.update({
                "running": True,
                "started_at": 1000.0,
                "consecutive_failures": 0,
                "retry_after": 0.0,
            })

        with patch.object(
            main,
            "refresh_news",
            side_effect=TimeoutError("provider timed out"),
        ) as refresh:
            with patch.object(main.time, "sleep"):
                main._cron_refresh_worker()

        assert refresh.call_count == main.REFRESH_MAX_ATTEMPTS
        with main._cron_refresh_lock:
            state = dict(main._cron_refresh_state)
        assert state["running"] is False
        assert state["last_error"] == "TimeoutError"
        assert state["last_attempt_count"] == main.REFRESH_MAX_ATTEMPTS
        assert state["consecutive_failures"] == 1
        assert state["retry_after"] > state["last_completed"]
        assert state["last_successful"] == old_state["last_successful"]
    finally:
        _restore_refresh_state(old_state)


def test_cron_endpoint_rejects_refresh_during_cooldown():
    old_state = _save_refresh_state()
    old_token = main.os.environ.get("KAIVOR_CRON_TOKEN")
    try:
        main.os.environ["KAIVOR_CRON_TOKEN"] = "test-token"
        with main._cron_refresh_lock:
            main._cron_refresh_state.update({
                "running": False,
                "retry_after": main.time.time() + 30,
            })

        response = main.app.test_client().post(
            "/api/cron/refresh",
            headers={"Authorization": "Bearer test-token"},
        )
        payload = response.get_json()
        assert response.status_code == 429
        assert payload["status"] == "cooldown"
        assert payload["retry_after_seconds"] > 0
    finally:
        _restore_refresh_state(old_state)
        if old_token is None:
            main.os.environ.pop("KAIVOR_CRON_TOKEN", None)
        else:
            main.os.environ["KAIVOR_CRON_TOKEN"] = old_token


def test_cold_start_recovery_respects_failure_cooldown():
    old_state = _save_refresh_state()
    old_articles = main._news_cache["articles"]
    try:
        with main._news_lock:
            main._news_cache["articles"] = []
        with main._cron_refresh_lock:
            main._cron_refresh_state.update({
                "running": False,
                "retry_after": main.time.time() + 30,
            })

        with patch.object(main.threading, "Thread") as thread:
            assert main._ensure_news_refresh_started() is False
            thread.assert_not_called()
    finally:
        with main._news_lock:
            main._news_cache["articles"] = old_articles
        _restore_refresh_state(old_state)
