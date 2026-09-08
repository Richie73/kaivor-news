"""Tests for the Kaivor OpenAI-compatible API adapter."""

import json
import os
import sys
from unittest.mock import patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.api.openai_server import _normalise_messages, _build_request, MODEL_ID


def main():
    messages = _normalise_messages([
        {"role": "system", "content": "client instruction"},
        {"role": "user", "content": "Hello Kaivor"},
    ])
    assert messages[-1]["content"] == "Hello Kaivor"

    class FakeRAG:
        def context(self, question):
            return {"context": "", "sources": []}

    with patch("core.api.openai_server.RAGService", return_value=FakeRAG()):
        request, rag = _build_request(messages, "chat")

    assert request.user == "Hello Kaivor"
    assert request.history == []
    assert rag["sources"] == []
    assert MODEL_ID == "kaivor"

    print("✓ OpenAI-compatible API adapter")


if __name__ == "__main__":
    main()
