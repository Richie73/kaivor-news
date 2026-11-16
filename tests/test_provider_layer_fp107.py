"""FP107: one working provider layer (core/providers).

Before this milestone the engine had three overlapping provider
sketches (ai/providers.py, core/ai/*, core/providers/*) and the
live app's three AI callers (chat, RAMS, receipts) each ran their
own duplicated chain. core/providers is now THE provider layer:
BaseProvider (name, configured(), generate(request, model)),
real generate() on OpenRouter, OpenAI and DeepSeek, keys from
environment variables at call time, and
ProviderManager.generate_with_fallback() running a request down
the priority chain from config/providers.json. FP108 wires the
live callers to it; this milestone changes no live behaviour.
"""
from unittest.mock import patch

import pytest
import requests

from core.ai.request import AIRequest
from core.providers.base import ProviderError
from core.providers.deepseek import DeepSeekProvider
from core.providers.manager import ProviderManager
from core.providers.openai import OpenAIProvider
from core.providers.openrouter import OpenRouterProvider


class FakeResponse:
    def __init__(self, payload=None, status_code=200, error=None):
        self._payload = payload if payload is not None else {
            "choices": [{"message": {"content": "hello from the model"}}]
        }
        self.status_code = status_code
        self._error = error

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self._error is not None:
            raise self._error


def clear_keys(monkeypatch):
    for var in ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY"):
        monkeypatch.delenv(var, raising=False)


def test_manager_registers_all_providers():
    manager = ProviderManager()
    assert manager.list() == ["Anthropic", "DeepSeek", "Google", "Ollama", "OpenAI", "OpenRouter"]
    assert manager.get("OpenRouter").name == "OpenRouter"
    assert manager.get("Nope") is None


def test_manager_orders_by_priority_from_config():
    manager = ProviderManager()
    # FP108: config/providers.json enables DeepSeek (1), OpenRouter
    # (2) and OpenAI (3) — OpenAI is the live fallback everywhere.
    assert manager.ordered() == ["DeepSeek", "OpenRouter", "OpenAI"]
    assert manager.fallback_chain() == ["DeepSeek", "OpenRouter", "OpenAI"]
    assert manager.primary() == "DeepSeek"
    assert manager.next_provider("DeepSeek") == "OpenRouter"
    assert manager.next_provider("OpenRouter") == "OpenAI"
    assert manager.next_provider("OpenAI") is None
    assert manager.next_provider("Nope") is None


def test_manager_health(monkeypatch):
    clear_keys(monkeypatch)
    manager = ProviderManager()
    assert manager.health() == {
        "OpenRouter": False, "DeepSeek": False, "OpenAI": False,
        "Anthropic": False, "Google": False, "Ollama": False,
    }
    monkeypatch.setenv("OPENROUTER_API_KEY", "key")
    assert manager.health()["OpenRouter"] is True
    assert manager.health()["OpenAI"] is False


def test_openrouter_generate(monkeypatch):
    clear_keys(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    request = AIRequest(user="Hi", system="Be brief.", temperature=0.5, max_tokens=100)
    with patch("core.providers.openrouter.requests.post", return_value=FakeResponse()) as post:
        assert OpenRouterProvider().generate(request) == "hello from the model"
    post.assert_called_once()
    args, kwargs = post.call_args
    assert args[0] == "https://openrouter.ai/api/v1/chat/completions"
    assert kwargs["headers"]["Authorization"] == "Bearer or-key"
    payload = kwargs["json"]
    assert payload["model"] == "deepseek/deepseek-chat"
    assert payload["messages"] == [
        {"role": "system", "content": "Be brief."},
        {"role": "user", "content": "Hi"},
    ]
    assert payload["temperature"] == 0.5
    assert payload["max_tokens"] == 100


def test_openrouter_generate_model_override(monkeypatch):
    clear_keys(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    with patch("core.providers.openrouter.requests.post", return_value=FakeResponse()) as post:
        OpenRouterProvider().generate(AIRequest(user="Hi"), model="google/gemini-2.5-flash")
    assert post.call_args[1]["json"]["model"] == "google/gemini-2.5-flash"


def test_openrouter_generate_errors(monkeypatch):
    clear_keys(monkeypatch)
    with pytest.raises(ProviderError, match="not configured"):
        OpenRouterProvider().generate(AIRequest(user="Hi"))
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    http_error = requests.HTTPError("401")
    with patch("core.providers.openrouter.requests.post", return_value=FakeResponse(error=http_error)):
        with pytest.raises(ProviderError, match="request failed"):
            OpenRouterProvider().generate(AIRequest(user="Hi"))
    with patch("core.providers.openrouter.requests.post", return_value=FakeResponse(payload={"nope": True})):
        with pytest.raises(ProviderError, match="unexpected response"):
            OpenRouterProvider().generate(AIRequest(user="Hi"))


def test_openai_generate(monkeypatch):
    clear_keys(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "oa-key")
    with patch("core.providers.openai.requests.post", return_value=FakeResponse()) as post:
        assert OpenAIProvider().generate(AIRequest(user="Hi")) == "hello from the model"
    args, kwargs = post.call_args
    assert args[0] == "https://api.openai.com/v1/chat/completions"
    assert kwargs["headers"]["Authorization"] == "Bearer oa-key"
    assert kwargs["json"]["model"] == "gpt-4o-mini"


def test_deepseek_generate(monkeypatch):
    clear_keys(monkeypatch)
    assert DeepSeekProvider().configured() is False
    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-key")
    assert DeepSeekProvider().configured() is True
    with patch("core.providers.deepseek.requests.post", return_value=FakeResponse()) as post:
        assert DeepSeekProvider().generate(AIRequest(user="Hi")) == "hello from the model"
    args, kwargs = post.call_args
    assert args[0] == "https://api.deepseek.com/chat/completions"
    assert kwargs["json"]["model"] == "deepseek-chat"


def test_generate_with_fallback_uses_default_chain(monkeypatch):
    clear_keys(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    manager = ProviderManager()
    with patch("core.providers.openrouter.requests.post", return_value=FakeResponse()):
        name, text = manager.generate_with_fallback(AIRequest(user="Hi"))
    # DeepSeek is priority 1 but unconfigured, so it is skipped.
    assert name == "OpenRouter"
    assert text == "hello from the model"


def test_generate_with_fallback_falls_back_on_failure(monkeypatch):
    clear_keys(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    monkeypatch.setenv("OPENAI_API_KEY", "oa-key")
    manager = ProviderManager()

    def fake_post(url, **kwargs):
        # Both provider modules import the same requests module, so
        # patch it once and key the behaviour by URL.
        if "openrouter" in url:
            raise requests.ConnectionError("down")
        return FakeResponse()

    with patch("requests.post", side_effect=fake_post):
        name, text = manager.generate_with_fallback(
            AIRequest(user="Hi"), chain=["OpenRouter", "OpenAI"]
        )
    assert name == "OpenAI"
    assert text == "hello from the model"


def test_generate_with_fallback_all_fail(monkeypatch):
    clear_keys(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    manager = ProviderManager()
    with patch("core.providers.openrouter.requests.post", side_effect=requests.ConnectionError("down")):
        with pytest.raises(ProviderError) as excinfo:
            manager.generate_with_fallback(AIRequest(user="Hi"), chain=["DeepSeek", "OpenRouter", "Missing"])
    message = str(excinfo.value)
    assert "DeepSeek: not configured" in message
    assert "OpenRouter:" in message
    assert "Missing: not registered" in message


def test_ai_request_messages_order():
    request = AIRequest(
        user="What is this?",
        system="Answer briefly.",
        context="Some background.",
        history=[{"role": "assistant", "content": "Earlier reply."}],
    )
    assert request.messages == [
        {"role": "system", "content": "Answer briefly."},
        {"role": "system", "content": "Knowledge Context:\n\nSome background."},
        {"role": "assistant", "content": "Earlier reply."},
        {"role": "user", "content": "What is this?"},
    ]
