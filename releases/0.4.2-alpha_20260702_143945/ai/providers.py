"""
Kaivor Provider Layer
"""

import requests

from config.settings import (
    OPENROUTER_URL,
    AI_TIMEOUT,
)

from config.local_config import OPENROUTER_API_KEY

from ai.exceptions import ProviderError


class OpenRouterProvider:

    def __init__(self):

        self.url = OPENROUTER_URL
        self.api_key = OPENROUTER_API_KEY

    def chat(
        self,
        model,
        messages,
        temperature=0.3,
    ):

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        try:

            response = requests.post(
                self.url,
                headers=headers,
                json=payload,
                timeout=AI_TIMEOUT,
            )

            response.raise_for_status()

            return response.json()

        except Exception as e:

            raise ProviderError(str(e))()
