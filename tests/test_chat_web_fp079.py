"""FP079: web browsing in the chat hub — Brave search behind a toggle."""

from pathlib import Path
from unittest.mock import Mock, patch

import requests as requests_lib

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


def _chat(monkeypatch, **overrides):
    client = _authed_client(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    payload = {"messages": [{"role": "user", "content": "Who won the match?"}]}
    payload.update(overrides)
    return client, payload


# --- search helper ---

def test_search_web_for_chat_returns_clean_results(monkeypatch):
    monkeypatch.setenv("BRAVE_API_KEY", "test-brave")
    with patch.object(main.requests, "get", return_value=_brave_response(BRAVE_RESULTS)) as get:
        results, error = main.search_web_for_chat("test query")
    assert error is None
    assert results == BRAVE_RESULTS
    assert get.call_args.args[0] == "https://api.search.brave.com/res/v1/web/search"
    assert get.call_args.kwargs["params"] == {"q": "test query", "count": 5}
    assert get.call_args.kwargs["headers"] == {"X-Subscription-Token": "test-brave"}


def test_search_web_for_chat_skips_non_http_urls(monkeypatch):
    monkeypatch.setenv("BRAVE_API_KEY", "test-brave")
    mixed = BRAVE_RESULTS + [
        {"title": "Bad", "url": "javascript:alert(1)", "description": "nope"},
        {"title": "Relative", "url": "/local/page", "description": "nope"},
    ]
    with patch.object(main.requests, "get", return_value=_brave_response(mixed)):
        results, error = main.search_web_for_chat("test query")
    assert error is None
    assert results == BRAVE_RESULTS


def test_search_web_for_chat_reports_missing_key(monkeypatch):
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    results, error = main.search_web_for_chat("test query")
    assert results is None
    assert error == "no_key"


def test_search_web_for_chat_reports_failures(monkeypatch):
    monkeypatch.setenv("BRAVE_API_KEY", "test-brave")
    failed = Mock()
    failed.status_code = 500
    with patch.object(main.requests, "get", return_value=failed):
        results, error = main.search_web_for_chat("test query")
    assert results is None
    assert error == "failed"
    with patch.object(main.requests, "get", side_effect=requests_lib.RequestException("down")):
        results, error = main.search_web_for_chat("test query")
    assert results is None
    assert error == "failed"


# --- /api/chat with web on ---

def test_chat_web_searches_and_returns_sources(monkeypatch):
    client, payload = _chat(monkeypatch, web=True)
    monkeypatch.setenv("BRAVE_API_KEY", "test-brave")
    with (
        patch.object(main.requests, "get", return_value=_brave_response(BRAVE_RESULTS)) as get,
        patch.object(main.requests, "post", return_value=_provider_response("Team A won [1].")) as post,
    ):
        response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["reply"] == "Team A won [1]."
    assert data["web_used"] is True
    assert data["sources"] == [
        {"title": "First result", "url": "https://example.com/one"},
        {"title": "Second result", "url": "https://example.com/two"},
    ]
    assert get.call_args.kwargs["params"]["q"] == "Who won the match?"
    system = post.call_args.kwargs["json"]["messages"][0]["content"]
    assert "First result" in system
    assert "https://example.com/one" in system
    assert "Second page summary." in system


def test_chat_web_uses_last_user_message_as_query(monkeypatch):
    client = _authed_client(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("BRAVE_API_KEY", "test-brave")
    history = [
        {"role": "user", "content": "Tell me about the FA Cup."},
        {"role": "assistant", "content": "It is a knockout competition."},
        {"role": "user", "content": "Who won it in 2025?"},
    ]
    with (
        patch.object(main.requests, "get", return_value=_brave_response(BRAVE_RESULTS)) as get,
        patch.object(main.requests, "post", return_value=_provider_response("Crystal Palace [1].")),
    ):
        response = client.post("/api/chat", json={"messages": history, "web": True})
    assert response.status_code == 200
    assert get.call_args.kwargs["params"]["q"] == "Who won it in 2025?"


def test_chat_web_truncates_long_query(monkeypatch):
    client, payload = _chat(monkeypatch, web=True)
    payload["messages"] = [{"role": "user", "content": "x" * 4000}]
    monkeypatch.setenv("BRAVE_API_KEY", "test-brave")
    with (
        patch.object(main.requests, "get", return_value=_brave_response([])) as get,
        patch.object(main.requests, "post", return_value=_provider_response("ok")),
    ):
        response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    assert len(get.call_args.kwargs["params"]["q"]) == 400


def test_chat_web_without_brave_key_returns_503(monkeypatch):
    client, payload = _chat(monkeypatch, web=True)
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    with patch.object(main.requests, "post", return_value=_provider_response("nope")) as post:
        response = client.post("/api/chat", json=payload)
    assert response.status_code == 503
    assert "Brave" in response.get_json()["error"]
    post.assert_not_called()


def test_chat_web_failure_returns_503(monkeypatch):
    client, payload = _chat(monkeypatch, web=True)
    monkeypatch.setenv("BRAVE_API_KEY", "test-brave")
    failed = Mock()
    failed.status_code = 429
    with (
        patch.object(main.requests, "get", return_value=failed),
        patch.object(main.requests, "post", return_value=_provider_response("nope")) as post,
    ):
        response = client.post("/api/chat", json=payload)
    assert response.status_code == 503
    assert response.get_json()["success"] is False
    post.assert_not_called()


def test_chat_web_empty_results_answer_normally(monkeypatch):
    client, payload = _chat(monkeypatch, web=True)
    monkeypatch.setenv("BRAVE_API_KEY", "test-brave")
    with (
        patch.object(main.requests, "get", return_value=_brave_response([])),
        patch.object(main.requests, "post", return_value=_provider_response("I do not know.")) as post,
    ):
        response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["web_used"] is False
    assert data["sources"] == []
    system = post.call_args.kwargs["json"]["messages"][0]["content"]
    assert "web search results" not in system


# --- /api/chat with web off (unchanged behaviour) ---

def test_chat_without_web_flag_does_not_search(monkeypatch):
    client, payload = _chat(monkeypatch)
    monkeypatch.setenv("BRAVE_API_KEY", "test-brave")
    with (
        patch.object(main.requests, "get") as get,
        patch.object(main.requests, "post", return_value=_provider_response("Hello back")),
    ):
        response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    get.assert_not_called()
    assert response.get_json()["web_used"] is False
    assert response.get_json()["sources"] == []


def test_chat_with_web_false_does_not_search(monkeypatch):
    client, payload = _chat(monkeypatch, web=False)
    monkeypatch.setenv("BRAVE_API_KEY", "test-brave")
    with (
        patch.object(main.requests, "get") as get,
        patch.object(main.requests, "post", return_value=_provider_response("Hello back")),
    ):
        response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    get.assert_not_called()


# --- template ---

def _template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def test_template_has_web_toggle_and_sources():
    text = _template_text()
    assert 'id="chat-web"' in text
    assert "kaivor-chat-web" in text
    assert "function saveChatWebToggle()" in text
    assert "function showChatWebNote(" in text
    assert ".chat-sources" in text
    assert ".chat-web-toggle" in text
    assert "Sources:" in text
    assert "web: webOn" in text
    assert "message.sources" in text
