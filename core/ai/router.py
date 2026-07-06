"""
Kaivor AI Router
"""

from config.config import ConfigManager
from core.ai.models import ModelRegistry
from core.ai.scoring import ProviderScorer
from core.ai.tasks import AITasks
from core.providers.manager import ProviderManager


class AIRouter:
    """Selects the best available AI provider."""

    def __init__(self):
        self.manager = ProviderManager()
        self.scorer = ProviderScorer()
        self.models = ModelRegistry()
        self.config = ConfigManager()

    def select(self, task=AITasks.CHAT):

        providers = self.available(task)

        if not providers:
            raise RuntimeError(
                f"No configured providers available for task: {task}"
            )

        ranked = self.scorer.rank(providers)

        return ranked[0]

    def available(self, task=AITasks.CHAT):

        routing = self.config.task_routing()

        preferred = routing.get(task.lower())

        providers = []

        if preferred:

            provider = self.manager.get(preferred)

            if (
                provider
                and self.models.supports(provider.name, task.lower())
            ):
                try:
                    if provider.configured():
                        providers.append(provider)
                except Exception:
                    pass

        if providers:
            return providers

        for name in self.manager.fallback_chain():

            provider = self.manager.get(name)

            if provider is None:
                continue

            if not self.models.supports(provider.name, task.lower()):
                continue

            try:
                if provider.configured():
                    providers.append(provider)
            except Exception:
                pass

        return providers
