#!/usr/bin/env python3
"""FP008 regression tests for the OpenAI-compatible API adapter."""
from __future__ import annotations
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.api.openai_server import _error, _model_payload, _response_payload


class FP008ApiTests(unittest.TestCase):
    def test_model_payload_shape(self):
        payload = _model_payload()
        self.assertEqual(payload["object"], "list")
        self.assertTrue(payload["data"])
        model = payload["data"][0]
        self.assertEqual(model["id"], "kaivor")
        self.assertEqual(model["object"], "model")

    def test_response_payload_shape(self):
        payload = _response_payload(
            request_id="req-test",
            model="kaivor",
            content="hello",
        )
        self.assertEqual(payload["object"], "chat.completion")
        self.assertEqual(payload["id"], "req-test")
        self.assertEqual(payload["choices"][0]["message"]["content"], "hello")
        self.assertIn("usage", payload)

    def test_error_is_openai_style(self):
        payload = _error("bad request", "invalid_request_error", 400)
        self.assertEqual(payload["error"]["message"], "bad request")
        self.assertEqual(payload["error"]["type"], "invalid_request_error")

if __name__ == "__main__":
    unittest.main(verbosity=2)
