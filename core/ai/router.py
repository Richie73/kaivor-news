"""
Kaivor AI Router
"""

from core.providers.manager import ProviderManager
from core.ai.scoring import ProviderScorer


class AIRouter:
    """Selects the best available AI provider."""

    STRATEGY_PRIORITY = "priority"
    STRATEGY_FASTEST = "fastest"
    STRATEGY_CHEAPEST = "cheapest"
    STRATEGY_BEST = "best"

    def __init__(self):
        self.manager = ProviderManager()
        self.scorer = ProviderScorer()

    def select(self, strategy=STRATEGY_PRIORITY):

        providers = self.available()

        if not providers:
            raise RuntimeError(
                "No configured AI providers available."
            )

        ranked = self.scorer.rank(providers)

        return ranked[0]

    def available(self):

        providers = []

        for name in self.manager.fallback_chain():

            provider = self.manager.get(name)

            if provider is None:
                continue

            try:

                if provider.configured():
                    providers.append(provider)

            except Exception:
                pass

        return providers
