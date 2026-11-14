"""FP079.1: visible web status in the chat hub — a badge on web questions,
a status line under web replies, and one server log line per chat request."""

from pathlib import Path
from unittest.mock import Mock, patch

import main

PIN = "test-pin-1234"
SECRET = "s" * 32

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"

BRAVE_RESULTS = [
    {"title": "First result", "url": "https://example.com/one", "description": "First page summary."},
    {"title": "Second result", "url": "https://example.com/two", "description": "Second page summary."},
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


# --- server log line (visible in the Render logs; no message content) ---

def test_chat_logs_web_outcome(monkeypatch, capsys):
    client = _authed_client(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("BRAVE_API_KEY", "test-brave")
    with (
        patch.object(main.requests, "get", return_value=_brave_response(BRAVE_RESULTS)),
        patch.object(main.requests, "post", return_value=_provider_response("ok")),
    ):
        response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "Gold price?"}], "web": True})
    assert response.status_code == 200
    assert "[chat] web_requested=True web_used=True sources=2" in capsys.readouterr().out


def test_chat_logs_web_off(monkeypatch, capsys):
    client = _authed_client(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    with patch.object(main.requests, "post", return_value=_provider_response("ok")):
        response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "Hello"}]})
    assert response.status_code == 200
    assert "[chat] web_requested=False web_used=False sources=0" in capsys.readouterr().out


def test_chat_logs_missing_brave_key(monkeypatch, capsys):
    client = _authed_client(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "Gold price?"}], "web": True})
    assert response.status_code == 503
    assert "[chat] web_requested=True web_error=no_key" in capsys.readouterr().out


def test_chat_logs_search_failure(monkeypatch, capsys):
    client = _authed_client(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("BRAVE_API_KEY", "test-brave")
    failed = Mock()
    failed.status_code = 429
    with patch.object(main.requests, "get", return_value=failed):
        response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "Gold price?"}], "web": True})
    assert response.status_code == 503
    assert "[chat] web_requested=True web_error=failed" in capsys.readouterr().out


# --- template ---

def _template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def test_template_has_web_badge_and_status():
    text = _template_text()
    assert ".chat-web-badge" in text
    assert "message.web" in text
    assert "userMessage.web = true" in text
    assert "webStatusNote" in text
    assert "Web search ·" in text
    assert "Web search found nothing." in text
    assert "hasn't updated yet" in text
