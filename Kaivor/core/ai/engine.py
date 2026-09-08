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

from core.knowledge.context_prompt import KnowledgePrompt
from core.knowledge.rag_service import RAGService


class AIEngine:
    """Central AI execution engine."""

    def __init__(self):
        self.router = AIRouter()
        self.logger = UsageLogger()
        self.stats = ProviderStats()
        self.prompt_builder = PromptBuilder()
        self.conversation = ConversationManager()
        self.config = Config()
        self.rag = RAGService()
        self.last_sources = []
        self.last_provider = None
        self.last_model = None

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

        rag = self.rag.context(prompt)

        knowledge_prompt = KnowledgePrompt.build(
            prompt,
            rag["context"],
        )

        messages = self.prompt_builder.build(
            task=task,
            user=knowledge_prompt,
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
            user=knowledge_prompt,
            system=system,
            history=request_history[:-1],
            temperature=self.config.get("temperature", 0.2),
            max_tokens=self.config.get("max_tokens", 2048),
        )

        providers = self.router.failover(task)

        response = None
        selected_provider = None

        retry_attempts = self.config.get(
            "retry_attempts",
            2,
        )

        for provider in providers:

            attempts = retry_attempts

            while attempts > 0:

                try:
                    start = time.perf_counter()

                    response = provider.generate(request)

                    elapsed = time.perf_counter() - start

                    self.stats.record_success(
                        provider.name,
                        elapsed,
                    )

                    selected_provider = provider
                    attempts = 0
                    break

                except Exception:
                    attempts -= 1

                    self.stats.record_failure(
                        provider.name,
                    )

            if response is not None:
                break

        if response is None or selected_provider is None:
            raise RuntimeError("All providers failed.")

        self.last_provider = selected_provider.name
        self.last_model = getattr(
            selected_provider,
            "last_model",
            self.config.get("default_model", "unknown"),
        )

        if self.config.get("conversation_memory", True):
            self.conversation.add_user(prompt)
            self.conversation.add_assistant(response)

        self.logger.log(
            provider=selected_provider.name,
            model=self.last_model,
            prompt=prompt,
            response=response,
        )

        self.last_sources = rag["sources"]

        return response
