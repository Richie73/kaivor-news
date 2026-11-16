"""FP108: route the AI callers through the provider layer.

FP107 built one working provider layer (core/providers); this
milestone wires the live callers to it: the chat hub, the
article question route, the story intelligence drawer, the RAMS
drafter and the receipt reader. Each caller's old hand-rolled
provider loop is gone; ProviderManager.generate_with_fallback
runs the priority chain from config/providers.json (OpenRouter,
then OpenAI — OpenAI was enabled there in this milestone).

Deliberate exception: /api/ai_brief keeps its own chain. Its
per-provider brief validation and reason-code diagnostics
(malformed_provider_response, provider_request_failed, ...) are
bespoke, and forcing them through the manager would weaken the
diagnostics or complicate the manager for one caller.

The receipt reader uses an OpenRouter-only chain: its vision
model is OpenRouter-specific, so an OpenAI fallback with the
same model name would fail.
"""
from unittest.mock import patch

import pytest
import requests

import main
import receipt_reader
from core.ai.request import AIRequest
from core.providers.base import ProviderError
from core.providers.openrouter import OpenRouterProvider
from receipt_reader import ReceiptReadError, read_receipt

TINY_JPEG = "data:image/jpeg;base64,/9j/4AAQSkZJRg=="


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
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def clear_keys(monkeypatch):
    for var in ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY"):
        monkeypatch.delenv(var, raising=False)


# --- AIRequest bridges ---

def test_ai_request_direct_messages_pass_through_verbatim():
    direct = [
        {"role": "system", "content": "System."},
        {"role": "assistant", "content": "Earlier."},
        {"role": "user", "content": "Now?"},
    ]
    request = AIRequest(user="ignored", system="ignored", direct_messages=direct)
    assert request.messages == direct
    assert request.messages is not direct


def test_ai_request_image_message_is_multimodal():
    request = AIRequest(user="Read this.", image_data_url=TINY_JPEG)
    assert request.messages == [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Read this."},
                {"type": "image_url", "image_url": {"url": TINY_JPEG}},
            ],
        }
    ]


def test_providers_reject_empty_replies(monkeypatch):
    clear_keys(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    empty = FakeResponse(payload={"choices": [{"message": {"content": "   "}}]})
    with patch("core.providers.openrouter.requests.post", return_value=empty):
        with pytest.raises(ProviderError, match="empty reply"):
            OpenRouterProvider().generate(AIRequest(user="Hi"))


# --- chat hub ---

def test_chat_falls_back_to_openai(monkeypatch, authed_client):
    clear_keys(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "key-1")
    monkeypatch.setenv("OPENAI_API_KEY", "key-2")
    calls = []

    def fake_post(url, **kwargs):
        calls.append(url)
        if "openrouter" in url:
            return FakeResponse(status_code=500, error=requests.HTTPError("500"))
        return FakeResponse(payload={"choices": [{"message": {"content": "Fallback reply"}}]})

    with patch.object(main.requests, "post", side_effect=fake_post):
        response = authed_client.post("/api/chat", json={"messages": [{"role": "user", "content": "Hello"}]})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["reply"] == "Fallback reply"
    assert payload["provider"] == "OpenAI"
    assert len(calls) == 2


# --- ask AI + story intelligence ---

def test_ask_ai_uses_provider_layer(monkeypatch, authed_client):
    clear_keys(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "key-1")
    with patch.object(main.requests, "post", return_value=FakeResponse(payload={"choices": [{"message": {"content": "The article says X."}}]})) as post:
        response = authed_client.post(
            "/api/ask_ai",
            json={"question": "What happened?", "title": "Big news", "description": "Something happened."},
        )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["answer"] == "The article says X."
    assert payload["provider"] == "OpenRouter"
    sent = post.call_args.kwargs["json"]
    assert sent["model"] == "deepseek/deepseek-chat"
    assert "Big news" in sent["messages"][1]["content"]


def test_story_intelligence_uses_provider_layer(monkeypatch, authed_client):
    clear_keys(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "key-1")
    analysis = "WHAT WE KNOW\nA long analysis " + "x" * 100
    with patch.object(main.requests, "post", return_value=FakeResponse(payload={"choices": [{"message": {"content": analysis}}]})):
        response = authed_client.post(
            "/api/story_intelligence",
            json={"article": {"title": "Big news", "description": "Something happened."}},
        )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["analysis"] == analysis
    assert payload["provider"] == "OpenRouter"


def test_story_intelligence_falls_back_to_deterministic(monkeypatch, authed_client):
    clear_keys(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "key-1")
    with patch.object(main.requests, "post", side_effect=requests.ConnectionError("down")):
        response = authed_client.post(
            "/api/story_intelligence",
            json={"article": {"title": "Big news", "description": "Something happened."}},
        )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["fallback"] is True


# --- receipts ---

def test_receipt_uses_openrouter_only_chain(monkeypatch):
    clear_keys(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "key-1")
    monkeypatch.setenv("OPENAI_API_KEY", "key-2")
    calls = []

    def fake_post(url, **kwargs):
        calls.append(url)
        return FakeResponse(status_code=500, error=requests.HTTPError("500"))

    with patch.object(requests, "post", side_effect=fake_post):
        with pytest.raises(ReceiptReadError):
            read_receipt(TINY_JPEG)
    # OpenAI was configured but never tried: the vision model is
    # OpenRouter-specific, so there is no fallback for receipts.
    assert len(calls) == 1
    assert "openrouter" in calls[0]
