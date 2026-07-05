"""
DeepSeek Provider
"""

import json
import urllib.request
import urllib.error

from config import secrets
from core.providers.base import BaseProvider
from core.ai.request import AIRequest


class DeepSeekProvider(BaseProvider):
    """DeepSeek provider."""

    name = "DeepSeek"
    enabled = True

    API_URL = "https://api.deepseek.com/chat/completions"

    def configured(self):
        return bool(secrets.DEEPSEEK_API_KEY.strip())

    def generate(self, request: AIRequest):

        if not self.configured():
            raise RuntimeError("DeepSeek API key not configured.")

        payload = {
            "model": "deepseek-chat",
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        http_request = urllib.request.Request(
            self.API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {secrets.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(http_request, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))

            return data["choices"][0]["message"]["content"]

        except urllib.error.HTTPError as e:
            raise RuntimeError(
                f"DeepSeek HTTP {e.code}: {e.read().decode()}"
            )

        except urllib.error.URLError as e:
            raise RuntimeError(
                f"DeepSeek connection error: {e.reason}"
            )
