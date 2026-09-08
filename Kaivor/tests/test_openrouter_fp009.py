#!/usr/bin/env python3
"""FP009 tests for the OpenRouter provider and engine failover bookkeeping."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import secrets
from core.ai.request import AIRequest
from core.providers.openrouter import OpenRouterProvider


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


class OpenRouterFP009Tests(unittest.TestCase):

    def setUp(self):
        self.old_key = getattr(secrets, "OPENROUTER_API_KEY", "")
        secrets.OPENROUTER_API_KEY = "test-key"

    def tearDown(self):
        secrets.OPENROUTER_API_KEY = self.old_key

    def test_configured(self):
        provider = OpenRouterProvider()
        self.assertTrue(provider.configured())

    def test_generate_uses_request_messages(self):
        provider = OpenRouterProvider()
        request = AIRequest(
            user="Hello",
            system="You are Kaivor.",
            temperature=0.2,
            max_tokens=100,
        )

        captured = {}

        def fake_urlopen(req, timeout=0):
            captured["request"] = req
            captured["timeout"] = timeout
            return FakeResponse({
                "model": "openrouter/test-model",
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": "Hello from OpenRouter",
                    }
                }],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 4,
                    "total_tokens": 14,
                },
            })

        with patch("core.providers.openrouter.urllib.request.urlopen", fake_urlopen):
            result = provider.generate(request)

        self.assertEqual(result, "Hello from OpenRouter")
        self.assertEqual(provider.last_model, "openrouter/test-model")
        body = json.loads(captured["request"].data.decode("utf-8"))
        self.assertEqual(body["model"], "openrouter/auto")
        self.assertEqual(body["messages"][0]["role"], "system")
        self.assertEqual(body["messages"][-1]["content"], "Hello")
        self.assertEqual(captured["timeout"], 120)

    def test_missing_key_fails_cleanly(self):
        secrets.OPENROUTER_API_KEY = ""
        provider = OpenRouterProvider()
        self.assertFalse(provider.configured())
        with self.assertRaisesRegex(RuntimeError, "API key not configured"):
            provider.generate(AIRequest(user="Hello"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
