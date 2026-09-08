"""
Kaivor AI Brain
"""

import time

from ai.providers import OpenRouterProvider
from ai.response import AIResponse

from config.settings import (
    AI_DEFAULT_MODEL,
    AI_TEMPERATURE,
    AI_DEFAULT_PROVIDER,
)


class Brain:

    def __init__(self):

        self.provider = OpenRouterProvider()

    def run(
        self,
        task,
        prompt,
        model=None,
        temperature=None,
    ):

        if model is None:
            model = AI_DEFAULT_MODEL

        if temperature is None:
            temperature = AI_TEMPERATURE

        messages = [
            {
                "role": "system",
                "content": f"You are Kaivor. Current task: {task}.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]

        start = time.time()

        try:

            raw = self.provider.chat(
                model=model,
                messages=messages,
                temperature=temperature,
            )

            elapsed = round(time.time() - start, 2)

            content = raw["choices"][0]["message"]["content"]

            return AIResponse(
                success=True,
                content=content,
                raw=raw,
                model=model,
                provider=AI_DEFAULT_PROVIDER,
                elapsed=elapsed,
            )

        except Exception as e:

            elapsed = round(time.time() - start, 2)

            return AIResponse(
                success=False,
                content="",
                model=model,
                provider=AI_DEFAULT_PROVIDER,
                elapsed=elapsed,
                error=str(e),
            )