"""FP077: general chat hub — a chat view backed by /api/chat."""

from pathlib import Path
from unittest.mock import Mock, patch

import main

PIN = "test-pin-1234"
SECRET = "s" * 32

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"


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


# --- /api/chat route ---

def test_chat_returns_provider_reply(monkeypatch):
    client = _authed_client(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    with patch.object(main.requests, "post", return_value=_provider_response("Hello back")) as post:
        response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "Hello"}]})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["reply"] == "Hello back"
    assert payload["provider"] == "OpenRouter"
    sent = post.call_args.kwargs["json"]
    assert sent["model"] == "deepseek/deepseek-chat"
    assert sent["messages"][0]["role"] == "system"
    assert "Kaivor" in sent["messages"][0]["content"]
    assert sent["messages"][1] == {"role": "user", "content": "Hello"}


def test_chat_passes_history_through(monkeypatch):
    client = _authed_client(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    history = [
        {"role": "user", "content": "What is 2+2?"},
        {"role": "assistant", "content": "4."},
        {"role": "user", "content": "And 3+3?"},
    ]
    with patch.object(main.requests, "post", return_value=_provider_response("6.")) as post:
        response = client.post("/api/chat", json={"messages": history})
    assert response.status_code == 200
    sent = post.call_args.kwargs["json"]
    assert sent["messages"][1:] == history


def test_chat_rejects_bad_payloads(monkeypatch):
    client = _authed_client(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    assert client.post("/api/chat", json={}).status_code == 400
    assert client.post("/api/chat", json={"messages": "not-a-list"}).status_code == 400
    assert client.post("/api/chat", json={"messages": []}).status_code == 400
    assert client.post("/api/chat", json={"messages": [{"role": "system", "content": "x"}]}).status_code == 400
    assert client.post("/api/chat", json={"messages": [{"role": "user", "content": "  "}]}).status_code == 400
    assert client.post("/api/chat", json={"messages": [{"role": "user"}]}).status_code == 400
    too_many = [{"role": "user", "content": "hi"}] * 21
    assert client.post("/api/chat", json={"messages": too_many}).status_code == 400
    too_long = [{"role": "user", "content": "x" * 4001}]
    assert client.post("/api/chat", json={"messages": too_long}).status_code == 400


def test_chat_without_provider_returns_503(monkeypatch):
    client = _authed_client(monkeypatch)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "Hello"}]})
    assert response.status_code == 503
    assert response.get_json()["success"] is False


def test_chat_provider_failure_returns_503(monkeypatch):
    client = _authed_client(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    failed = Mock()
    failed.status_code = 500
    failed.json.return_value = {"error": {"message": "boom"}}
    with patch.object(main.requests, "post", return_value=failed):
        response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "Hello"}]})
    assert response.status_code == 503
    assert response.get_json()["success"] is False


def test_chat_route_is_behind_the_pin_gate():
    assert "api_chat" in main._GUARDED_MUTATION_ENDPOINTS


# --- template ---

def _template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def test_template_has_chat_view():
    text = _template_text()
    assert 'onclick="showChat(this)"' in text
    assert "function showChat(element)" in text
    assert "function sendChatMessage(event)" in text
    assert "function clearChatHistory()" in text
    assert 'id="chat-log"' in text
    assert 'id="chat-form"' in text
    assert 'id="chat-input"' in text
    assert "kaivor-chat-history" in text
    assert "fetch('/api/chat'" in text
    assert ".chat-log" in text
    assert ".chat-msg" in text
    assert "showChat(" in text


def test_chat_view_is_in_the_swipe_destinations():
    text = _template_text()
    assert '.chips .chip[onclick^="showChat("]' in text
