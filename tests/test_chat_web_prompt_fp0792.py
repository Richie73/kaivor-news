"""FP079.2: the web system prompt tells the model the search results ARE
its internet access, so it must not fall back to a "no live access"
refusal, and to point at the live sources when they do not carry the
exact figure."""

from unittest.mock import Mock, patch

import main

PIN = "test-pin-1234"
SECRET = "s" * 32

BRAVE_RESULTS = [
    {"title": "First result", "url": "https://example.com/one", "description": "First page summary."},
]


def _authed_client(monkeypatch):
    monkeypatch.setenv("KAIVOR_READING_PIN", PIN)
    monkeypatch.setenv("KAIVOR_SESSION_SECRET", SECRET)
    client = main.app.test_client()
    with client.session_transaction() as sess:
        sess["reading_authenticated"] = True
    return client


def _provider_response(text):
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"choices": [{"message": {"content": text}}]}
    return response


def _brave_response(results):
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"web": {"results": results}}
    return response


def test_web_prompt_forbids_no_access_refusal(monkeypatch):
    client = _authed_client(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("BRAVE_API_KEY", "test-brave")
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["payload"] = json
        return _provider_response("ok")

    with (
        patch.object(main.requests, "get", return_value=_brave_response(BRAVE_RESULTS)),
        patch.object(main.requests, "post", side_effect=fake_post),
    ):
        response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "Gold price?"}], "web": True})
    assert response.status_code == 200
    system_prompt = captured["payload"]["messages"][0]["content"]
    assert "ARE your internet access" in system_prompt
    assert "never say you lack internet access" in system_prompt
    assert "point to the sources that show it live" in system_prompt
    assert "[1] First result" in system_prompt


def test_web_off_prompt_has_no_web_instruction(monkeypatch):
    client = _authed_client(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["payload"] = json
        return _provider_response("ok")

    with patch.object(main.requests, "post", side_effect=fake_post):
        response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "Hello"}]})
    assert response.status_code == 200
    system_prompt = captured["payload"]["messages"][0]["content"]
    assert "internet access" not in system_prompt
