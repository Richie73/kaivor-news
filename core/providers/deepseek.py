"""
DeepSeek Provider — FP107: on the shared interface.

Calls the DeepSeek API directly (not via OpenRouter). The live
app reaches DeepSeek through OpenRouter today, so this provider
is unconfigured in practice (no DEEPSEEK_API_KEY set) and the
manager skips it — it is here for the day a direct key exists.
"""

import requests

from core.ai.request import AIRequest
from core.providers.base import BaseProvider, ProviderError


class DeepSeekProvider(BaseProvider):
    """DeepSeek provider."""

    name = "DeepSeek"

    default_model = "deepseek-chat"

    env_var = "DEEPSEEK_API_KEY"

    API_URL = "https://api.deepseek.com/chat/completions"

    def generate(self, request: AIRequest, model=None):
        api_key = self.api_key()
        if not api_key:
            raise ProviderError("DeepSeek API key not configured.")

        payload = {
            "model": model or self.default_model,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        try:
            response = requests.post(
                self.API_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=120,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ProviderError("DeepSeek returned an empty reply.")
            return content.strip()
        except requests.RequestException as exc:
            raise ProviderError(f"DeepSeek request failed: {exc}") from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError(f"DeepSeek returned an unexpected response: {exc}") from exc
