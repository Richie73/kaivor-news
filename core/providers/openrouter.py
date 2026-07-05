"""
OpenRouter Provider
"""

import json
import urllib.request

from core.ai.base import AIProvider


class OpenRouterProvider(AIProvider):
    """OpenRouter AI provider."""

    @property
    def name(self):
        return "OpenRouter"

    @property
    def enabled(self):
        return True

    def generate(self, prompt: str):
        raise NotImplementedError(
            "OpenRouter generation will be implemented in FP009."
        )

    def request(self, api_key, model, prompt):
        url = "https://openrouter.ai/api/v1/chat/completions"

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read())
