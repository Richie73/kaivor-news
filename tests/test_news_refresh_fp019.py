"""FP019 regression tests for version reporting and refresh diagnostics."""

import main


def test_health_reports_fp019_version_and_refresh_diagnostics():
    response = main.app.test_client().get("/api/health")
    assert response.status_code == 200
    payload = response.get_json()

    assert payload["version"] == "FP030.0"
    assert "cron_refresh_started_at" in payload
    assert "cron_refresh_running_age_seconds" in payload
    assert "cron_refresh_last_successful" in payload
    assert "cron_refresh_last_duration_seconds" in payload
    assert "cron_refresh_last_error" in payload


def test_health_reports_running_age_only_when_refresh_is_running():
    with main._cron_refresh_lock:
        old_state = dict(main._cron_refresh_state)
        main._cron_refresh_state["running"] = True
        main._cron_refresh_state["started_at"] = 1000.0

    try:
        response = main.app.test_client().get("/api/health")
        payload = response.get_json()
        assert payload["cron_refresh_running"] is True
        assert payload["cron_refresh_running_age_seconds"] is not None
        assert payload["cron_refresh_running_age_seconds"] >= 0
    finally:
        with main._cron_refresh_lock:
            main._cron_refresh_state.update(old_state)


def test_health_running_age_is_none_when_idle():
    with main._cron_refresh_lock:
        old_state = dict(main._cron_refresh_state)
        main._cron_refresh_state["running"] = False
        main._cron_refresh_state["started_at"] = 1000.0

    try:
        response = main.app.test_client().get("/api/health")
        payload = response.get_json()
        assert payload["cron_refresh_running"] is False
        assert payload["cron_refresh_running_age_seconds"] is None
    finally:
        with main._cron_refresh_lock:
            main._cron_refresh_state.update(old_state)
