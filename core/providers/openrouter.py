"""
OpenRouter Provider — FP107: real generate() on the shared interface.

OpenRouter is the live app's primary AI route (chat, RAMS and
receipts all call it first). The model is chosen per call because
tasks differ: deepseek/deepseek-chat for text, a vision model
for receipt images.
"""

import requests

from core.ai.request import AIRequest
from core.providers.base import BaseProvider, ProviderError


class OpenRouterProvider(BaseProvider):
    """OpenRouter AI provider."""

    name = "OpenRouter"

    default_model = "deepseek/deepseek-chat"

    env_var = "OPENROUTER_API_KEY"

    API_URL = "https://openrouter.ai/api/v1/chat/completions"

    def generate(self, request: AIRequest, model=None):
        api_key = self.api_key()
        if not api_key:
            raise ProviderError("OpenRouter API key not configured.")

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
                timeout=60,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.RequestException as exc:
            raise ProviderError(f"OpenRouter request failed: {exc}") from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError(f"OpenRouter returned an unexpected response: {exc}") from exc
