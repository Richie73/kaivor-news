"""FP069 tests for the shared PIN + signed-session gate on mutating API routes.

The gate reuses the Reading PIN pattern (app_security): the PIN
(KAIVOR_READING_PIN, 8+ characters) and session secret
(KAIVOR_SESSION_SECRET, 32+ characters) must be configured, and the session
must be unlocked via the Reading login. Until then, mutating routes fail
with a clear message — 503 when unconfigured, 401 when locked.
"""
from unittest.mock import patch

import pytest

import main

PIN = "test-pin-1234"
SECRET = "s" * 32

# (method, path, json payload, status the route itself returns once the
# guard passes). Invalid payloads are used deliberately: a 400 from the
# route proves the guard let the request through, with no network access.
GUARDED_CALLS = [
    ("POST", "/api/set_key", {"type": "bogus", "api_key": "x"}, 400),
    ("POST", "/api/add_feed", {"name": "", "url": ""}, 400),
    ("POST", "/api/save", {"article": "not-a-dict"}, 400),
    ("POST", "/api/story_timeline", {"article": {}}, 400),
    ("POST", "/api/story_intelligence", {"article": {}}, 400),
    ("POST", "/api/why_matters", {"article": {}}, 400),
    ("POST", "/api/ai_brief", {"article": {}}, 400),
    ("POST", "/api/chat", {"messages": "not-a-list"}, 400),
    ("PUT", "/api/relevance_profile", {"profile": "not-a-dict"}, 400),
]


def _configure(monkeypatch, pin=PIN, secret=SECRET):
    monkeypatch.setenv("KAIVOR_READING_PIN", pin)
    monkeypatch.setenv("KAIVOR_SESSION_SECRET", secret)


def _unconfigure(monkeypatch):
    monkeypatch.delenv("KAIVOR_READING_PIN", raising=False)
    monkeypatch.delenv("KAIVOR_SESSION_SECRET", raising=False)


def _call(client, method, path, payload):
    if method == "POST":
        return client.post(path, json=payload)
    if method == "PUT":
        return client.put(path, json=payload)
    raise AssertionError(f"unsupported method {method}")


@pytest.mark.parametrize("method,path,payload,_expected", GUARDED_CALLS)
def test_unconfigured_gate_returns_503(monkeypatch, method, path, payload, _expected):
    _unconfigure(monkeypatch)
    response = _call(main.app.test_client(), method, path, payload)
    assert response.status_code == 503
    assert "locked until" in response.get_json()["error"]
    assert "KAIVOR_READING_PIN" in response.get_json()["error"]


@pytest.mark.parametrize("method,path,payload,_expected", GUARDED_CALLS)
def test_configured_but_locked_returns_401(monkeypatch, method, path, payload, _expected):
    _configure(monkeypatch)
    response = _call(main.app.test_client(), method, path, payload)
    assert response.status_code == 401
    assert "unlock via the Reading section" in response.get_json()["error"]


@pytest.mark.parametrize("method,path,payload,expected", GUARDED_CALLS)
def test_authenticated_session_passes_guard(authed_client, method, path, payload, expected):
    response = _call(authed_client, method, path, payload)
    assert response.status_code == expected


def test_short_pin_is_not_configured(monkeypatch):
    _configure(monkeypatch, pin="short7!")
    response = main.app.test_client().post("/api/set_key", json={"type": "bogus", "api_key": "x"})
    assert response.status_code == 503


def test_short_session_secret_is_not_configured(monkeypatch):
    _configure(monkeypatch, secret="s" * 31)
    response = main.app.test_client().post("/api/set_key", json={"type": "bogus", "api_key": "x"})
    assert response.status_code == 503


def test_refresh_route_is_guarded(monkeypatch, authed_client):
    _unconfigure(monkeypatch)
    assert main.app.test_client().post("/api/refresh").status_code == 503
    _configure(monkeypatch)
    assert main.app.test_client().post("/api/refresh").status_code == 401
    with patch.object(main, "refresh_news", return_value=[]):
        response = authed_client.post("/api/refresh")
    assert response.status_code == 200
    assert response.get_json()["success"] is True


def test_finance_refresh_route_is_guarded(monkeypatch, authed_client):
    _unconfigure(monkeypatch)
    assert main.app.test_client().post("/api/finance/refresh").status_code == 503
    _configure(monkeypatch)
    assert main.app.test_client().post("/api/finance/refresh").status_code == 401
    with main._finance_refresh_lock:
        main._finance_refresh_state["running"] = False
    with patch.object(main.threading, "Thread") as thread:
        response = authed_client.post("/api/finance/refresh")
    assert response.status_code == 202
    assert response.get_json()["status"] == "started"
    thread.return_value.start.assert_called_once()
    with main._finance_refresh_lock:
        main._finance_refresh_state["running"] = False


def test_delete_saved_route_is_guarded(monkeypatch, authed_client):
    _unconfigure(monkeypatch)
    assert main.app.test_client().delete("/api/save/any-id").status_code == 503
    _configure(monkeypatch)
    assert main.app.test_client().delete("/api/save/any-id").status_code == 401
    with patch.object(main, "remove_saved_article", return_value=False):
        response = authed_client.delete("/api/save/any-id")
    assert response.status_code == 200


def test_ask_ai_route_is_guarded(monkeypatch, authed_client):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    _unconfigure(monkeypatch)
    assert main.app.test_client().post("/api/ask_ai", json={"question": "q"}).status_code == 503
    _configure(monkeypatch)
    assert main.app.test_client().post("/api/ask_ai", json={"question": "q"}).status_code == 401
    # Guard passed: the route itself reports no provider configured.
    response = authed_client.post("/api/ask_ai", json={"question": "q"})
    assert response.status_code == 503
    assert "No AI provider is configured" in response.get_json()["error"]


@pytest.mark.parametrize("path", ["/api/health", "/api/ticker", "/api/saved", "/api/relevance_profile"])
def test_get_routes_stay_open(monkeypatch, path):
    _unconfigure(monkeypatch)
    response = main.app.test_client().get(path)
    assert response.status_code == 200


def test_cron_keeps_its_own_token_check(monkeypatch):
    _unconfigure(monkeypatch)
    monkeypatch.delenv("KAIVOR_CRON_TOKEN", raising=False)
    response = main.app.test_client().post("/api/cron/refresh")
    assert response.status_code == 401
    # The cron route's own message, not the FP069 guard's.
    assert response.get_json()["error"] == "Unauthorized"


def test_reading_login_unlocks_news_mutations(monkeypatch):
    _configure(monkeypatch)
    client = main.app.test_client()
    response = client.post("/reading/login", data={"pin": PIN})
    assert response.status_code == 302
    response = client.post("/api/set_key", json={"type": "bogus", "api_key": "x"})
    assert response.status_code == 400


def test_wrong_pin_does_not_unlock(monkeypatch):
    _configure(monkeypatch)
    client = main.app.test_client()
    response = client.post("/reading/login", data={"pin": "wrong-pin-1"})
    assert response.status_code == 302
    assert "error=1" in response.headers["Location"]
    response = client.post("/api/set_key", json={"type": "bogus", "api_key": "x"})
    assert response.status_code == 401


def test_reading_logout_locks_news_mutations_again(monkeypatch):
    _configure(monkeypatch)
    client = main.app.test_client()
    client.post("/reading/login", data={"pin": PIN})
    assert client.post("/api/set_key", json={"type": "bogus", "api_key": "x"}).status_code == 400
    client.post("/reading/logout")
    assert client.post("/api/set_key", json={"type": "bogus", "api_key": "x"}).status_code == 401
