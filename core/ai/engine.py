"""
Kaivor AI Engine
"""

import time

from core.ai.conversation import ConversationManager
from core.ai.prompt_builder import PromptBuilder
from core.ai.provider_stats import ProviderStats
from core.ai.request import AIRequest
from core.ai.router import AIRouter
from core.ai.tasks import AITasks
from core.ai.usage import UsageLogger
from core.config import Config


class AIEngine:
    """Central AI execution engine."""

    def __init__(self):
        self.router = AIRouter()
        self.logger = UsageLogger()
        self.stats = ProviderStats()
        self.prompt_builder = PromptBuilder()
        self.conversation = ConversationManager()
        self.config = Config()

    def ask(self, task: str, prompt: str):

        valid_tasks = (
            AITasks.CHAT,
            AITasks.CODING,
            AITasks.RESEARCH,
            AITasks.WRITING,
            AITasks.RAMS,
            AITasks.EMAIL,
            AITasks.NEWS,
            AITasks.VISION,
        )

        if task not in valid_tasks:
            raise ValueError(f"Unknown AI task: {task}")

        history = []

        if self.config.get("conversation_memory", True):
            history = self.conversation.history()

        messages = self.prompt_builder.build(
            task=task,
            user=prompt,
            history=history,
        )

        system = self.config.get(
            "system_prompt",
            "You are Kaivor.",
        )

        request_history = []

        for message in messages:
            if message["role"] != "system":
                request_history.append(message)

        request = AIRequest(
            user=prompt,
            system=system,
            history=request_history[:-1],
            temperature=self.config.get("temperature", 0.2),
            max_tokens=self.config.get("max_tokens", 2048),
        )

        provider = self.router.select(task)

        try:
            start = time.perf_counter()

            response = provider.generate(request)

            elapsed = time.perf_counter() - start

            self.stats.record_success(
                provider.name,
                elapsed,
            )

        except Exception:
            self.stats.record_failure(provider.name)
            raise

        if self.config.get("conversation_memory", True):
            self.conversation.add_user(prompt)
            self.conversation.add_assistant(response)

        self.logger.log(
            provider=provider.name,
            model=self.config.get(
                "default_model",
                "deepseek-chat",
            ),
            prompt=prompt,
            response=response,
        )

        return response
