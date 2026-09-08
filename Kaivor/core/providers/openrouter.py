"""
OpenRouter Provider

OpenRouter exposes an OpenAI-compatible chat-completions API and provides
access to multiple model providers through one API key.
"""

import json
import urllib.error
import urllib.request

from config import secrets
from core.providers.base import BaseProvider
from core.ai.request import AIRequest


class OpenRouterProvider(BaseProvider):
    """OpenRouter AI provider."""

    name = "OpenRouter"
    enabled = True
    API_URL = "https://openrouter.ai/api/v1/chat/completions"

    def configured(self):
        """Return True when an OpenRouter API key is configured."""
        return bool(getattr(secrets, "OPENROUTER_API_KEY", "").strip())

    def _model(self):
        """Return the configured OpenRouter model."""
        # Environment override is useful for testing and deployment without
        # changing the project configuration.
        import os

        return (
            os.environ.get("KAIVOR_OPENROUTER_MODEL", "").strip()
            or self._config_model()
        )

    @staticmethod
    def _config_model():
        from pathlib import Path

        path = Path("config/ai.json")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return str(
                data.get("openrouter_model")
                or "openrouter/auto"
            )
        except (OSError, json.JSONDecodeError):
            return "openrouter/auto"

    def generate(self, request: AIRequest):
        """Generate a text response through OpenRouter."""
        if not self.configured():
            raise RuntimeError("OpenRouter API key not configured.")

        payload = {
            "model": self._model(),
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        http_request = urllib.request.Request(
            self.API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {secrets.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "X-Title": "Kaivor",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(http_request, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))

            choices = data.get("choices") or []
            if not choices:
                raise RuntimeError(
                    f"OpenRouter returned no choices: {data}"
                )

            message = choices[0].get("message") or {}
            content = message.get("content")

            if content is None:
                raise RuntimeError(
                    f"OpenRouter returned no message content: {data}"
                )

            # Keep metadata available for future usage accounting without
            # changing the provider interface used by the current engine.
            self.last_response = data
            self.last_model = data.get("model", self._model())

            return str(content)

        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"OpenRouter HTTP {e.code}: {detail}"
            ) from e

        except urllib.error.URLError as e:
            raise RuntimeError(
                f"OpenRouter connection error: {e.reason}"
            ) from e

    # Backwards-compatible helper retained for existing callers/tests.
    def request(self, api_key, model, prompt):
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }

        req = urllib.request.Request(
            self.API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-Title": "Kaivor",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
