"""FP095: a refresh button for the news.

POST /api/refresh used to run refresh_news() inline — about 90s
on Render, so a button tap would hang until gunicorn nearly timed
out. It now starts the same background worker the cron endpoint
uses (shared _start_background_refresh helper) and returns at
once; the page polls /api/health until news_last_updated moves,
then reloads onto the fresh list. The route stays PIN-guarded,
and a locked browser is told to unlock via Reading.
"""
from pathlib import Path
import re
import time
from unittest.mock import patch

import main

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "index.html"


def _save_refresh_state():
    return dict(main._cron_refresh_state)


def _restore_refresh_state(saved):
    with main._cron_refresh_lock:
        main._cron_refresh_state.update(saved)


def test_refresh_starts_background_worker(authed_client):
    saved = _save_refresh_state()
    try:
        with main._cron_refresh_lock:
            main._cron_refresh_state.update({"running": False, "retry_after": 0.0})
        with patch.object(main.threading, "Thread") as thread:
            response = authed_client.post("/api/refresh")
        assert response.status_code == 202
        assert response.get_json()["status"] == "started"
        assert thread.call_args.kwargs["name"] == "kaivor-manual-refresh"
        assert thread.call_args.kwargs["target"] is main._cron_refresh_worker
        thread.return_value.start.assert_called_once()
    finally:
        _restore_refresh_state(saved)


def test_refresh_reports_already_running(authed_client):
    saved = _save_refresh_state()
    try:
        with main._cron_refresh_lock:
            main._cron_refresh_state.update({"running": True, "retry_after": 0.0})
        with patch.object(main.threading, "Thread") as thread:
            response = authed_client.post("/api/refresh")
        assert response.status_code == 202
        assert response.get_json()["status"] == "already_running"
        thread.assert_not_called()
    finally:
        _restore_refresh_state(saved)


def test_refresh_reports_cooldown(authed_client):
    saved = _save_refresh_state()
    try:
        with main._cron_refresh_lock:
            main._cron_refresh_state.update(
                {"running": False, "retry_after": time.time() + 60}
            )
        with patch.object(main.threading, "Thread") as thread:
            response = authed_client.post("/api/refresh")
        assert response.status_code == 429
        assert response.get_json()["status"] == "cooldown"
        thread.assert_not_called()
    finally:
        _restore_refresh_state(saved)


def test_refresh_still_guarded_when_locked(monkeypatch):
    monkeypatch.setenv("KAIVOR_READING_PIN", "test-pin-1234")
    monkeypatch.setenv("KAIVOR_SESSION_SECRET", "s" * 48)
    response = main.app.test_client().post("/api/refresh")
    assert response.status_code == 401


def test_cron_endpoint_uses_shared_starter():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "def _start_background_refresh(thread_name):" in source
    cron = re.search(
        r"def api_cron_refresh\(\):(.*?)\n\n\ndef ",
        source,
        re.S,
    )
    assert cron, "api_cron_refresh missing"
    assert '_start_background_refresh("kaivor-cron-refresh")' in cron.group(1)


def test_refresh_button_markup():
    html = TEMPLATE.read_text(encoding="utf-8")
    assert 'id="section-title-row"' in html
    # FP111: the title-row button is now the single refresh button —
    # it follows the view via refreshCurrentView.
    assert 'id="refresh-btn"' in html
    assert 'onclick="refreshCurrentView(this)"' in html
    assert "↻ Refresh news" in html


def test_refresh_button_polls_health_then_reloads():
    html = TEMPLATE.read_text(encoding="utf-8")
    match = re.search(
        r"async function refreshNewsFromButton\(button\) \{(.*?)\n\}",
        html,
        re.S,
    )
    assert match, "refreshNewsFromButton missing"
    body = match.group(1)
    assert "fetch('/api/refresh', {method:'POST'" in body
    assert "response.status === 401 || response.status === 503" in body
    assert "Unlock Reading to refresh the news." in body
    assert "fetch('/api/health', {cache:'no-store'})" in body
    assert "Number(health.news_last_updated || 0) > beforeTs" in body
    assert "window.location.reload();" in body
    assert "Date.now() + 180000" in body
