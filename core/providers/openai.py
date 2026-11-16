"""
OpenAI Provider — FP107: real generate() on the shared interface.

OpenAI is the live app's fallback AI route (gpt-4o-mini) when
OpenRouter fails. Same request shape as every other provider.
"""

import requests

from core.ai.request import AIRequest
from core.providers.base import BaseProvider, ProviderError


class OpenAIProvider(BaseProvider):
    """OpenAI AI provider."""

    name = "OpenAI"

    default_model = "gpt-4o-mini"

    env_var = "OPENAI_API_KEY"

    API_URL = "https://api.openai.com/v1/chat/completions"

    def generate(self, request: AIRequest, model=None):
        api_key = self.api_key()
        if not api_key:
            raise ProviderError("OpenAI API key not configured.")

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
            content = response.json()["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ProviderError("OpenAI returned an empty reply.")
            return content.strip()
        except requests.RequestException as exc:
            raise ProviderError(f"OpenAI request failed: {exc}") from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError(f"OpenAI returned an unexpected response: {exc}") from exc
