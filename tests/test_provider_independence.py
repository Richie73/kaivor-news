
#!/usr/bin/env python3
"""FP009 provider-independence regression tests."""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.ai.engine import AIEngine
from core.ai.request import AIRequest
from core.ai.response import ProviderResponse
from core.api.openai_server import _build_request, _normalise_messages
from core.providers.openrouter import OpenRouterProvider


class FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


class FakeProvider:
    def __init__(self, name, responses, model="fake-model"):
        self.name = name
        self.responses = list(responses)
        self.model = model
        self.calls = 0

    def generate(self, request):
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeRouter:
    def __init__(self, providers):
        self.providers = providers

    def failover(self, task):
        return self.providers


class NoOpStats:
    def record_success(self, provider, latency):
        pass

    def record_failure(self, provider):
        pass


class NoOpLogger:
    def log(self, **kwargs):
        self.last = kwargs


class OpenRouterTests(unittest.TestCase):
    def test_openrouter_builds_canonical_payload_and_preserves_metadata(self):
        provider = OpenRouterProvider()
        request = AIRequest(
            user="Hello",
            system="You are Kaivor",
            history=[{"role": "user", "content": "Earlier"}],
            temperature=0.3,
            max_tokens=100,
        )
        payload = {
            "id": "gen-1",
            "model": "google/gemini-test",
            "choices": [{
                "message": {"role": "assistant", "content": "Hi"},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 3,
                "total_tokens": 15,
            },
        }
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}), patch(
            "core.providers.openrouter.urllib.request.urlopen",
            return_value=FakeHTTPResponse(payload),
        ) as mocked:
            result = provider.generate(request)

        self.assertEqual(result.content, "Hi")
        self.assertEqual(result.provider, "OpenRouter")
        self.assertEqual(result.model, "google/gemini-test")
        self.assertEqual(result.usage["total_tokens"], 15)
        sent = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(sent["model"], provider.model)
        self.assertEqual(sent["messages"][-1]["content"], "Hello")
        self.assertEqual(sent["temperature"], 0.3)
        self.assertEqual(sent["max_tokens"], 100)

    def test_openrouter_model_is_configurable(self):
        with patch.dict(os.environ, {"KAIVOR_OPENROUTER_MODEL": "openrouter/auto"}):
            provider = OpenRouterProvider()
            self.assertEqual(provider.model, "openrouter/auto")


class EngineTests(unittest.TestCase):
    def test_failover_uses_second_provider_and_preserves_metadata(self):
        first = FakeProvider("DeepSeek", [RuntimeError("down")])
        second = FakeProvider(
            "OpenRouter",
            [ProviderResponse(
                content="fallback answer",
                provider="OpenRouter",
                model="google/gemini-test",
                usage={"total_tokens": 9},
            )],
        )
        engine = AIEngine()
        engine.router = FakeRouter([first, second])
        engine.stats = NoOpStats()
        engine.logger = NoOpLogger()

        request = AIRequest(user="Test")
        result = engine.generate(request, task="chat", remember=False)

        self.assertEqual(result, "fallback answer")
        self.assertEqual(first.calls, 2)  # default retry_attempts is 2
        self.assertEqual(second.calls, 1)
        self.assertEqual(engine.last_provider, "OpenRouter")
        self.assertEqual(engine.last_model, "google/gemini-test")
        self.assertEqual(engine.last_usage["total_tokens"], 9)


class ConversationTests(unittest.TestCase):
    def test_api_request_preserves_full_history(self):
        messages = _normalise_messages([
            {"role": "system", "content": "Client system instruction"},
            {"role": "user", "content": "My name is Richie."},
            {"role": "assistant", "content": "Nice to meet you."},
            {"role": "user", "content": "What did I just tell you my name was?"},
        ])
        fake_engine = object.__new__(AIEngine)
        fake_engine.config = type("Config", (), {
            "get": lambda self, key, default=None: {
                "system_prompt": "You are Kaivor.",
                "temperature": 0.2,
                "max_tokens": 2048,
            }.get(key, default)
        })()
        fake_engine.rag = type("RAG", (), {
            "context": lambda self, question: {"context": "", "sources": []}
        })()

        with patch("core.api.openai_server.AIEngine", return_value=fake_engine):
            request, rag = _build_request(messages, "chat")

        self.assertEqual(len(request.history), 2)
        self.assertEqual(request.history[0]["content"], "My name is Richie.")
        self.assertEqual(request.history[1]["content"], "Nice to meet you.")
        self.assertIn("Client system instruction", request.system)
        self.assertEqual(request.user, "What did I just tell you my name was?")
        self.assertEqual(rag["sources"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
