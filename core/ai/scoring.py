"""
Kaivor Provider Scoring
"""

from core.ai.models import ModelRegistry
from core.ai.provider_stats import ProviderStats


class ProviderScorer:
    """Scores AI providers."""

    def __init__(self):
        self.stats = ProviderStats()
        self.models = ModelRegistry()

    def confidence(self, provider):

        summary = self.stats.summary().get(provider.name)

        if not summary:
            return 100

        total = (
            summary["success"]
            + summary["failure"]
        )

        if total == 0:
            return 100

        return round(
            summary["success"] / total * 100,
            1,
        )

    def score(self, provider):

        score = 0

        try:
            if provider.configured():
                score += 100
        except Exception:
            return 0

        summary = self.stats.summary().get(provider.name)

        if summary:

            score += summary["success"] * 2
            score -= summary["failure"] * 5

            latency = summary["average_latency"]

            if latency > 0:

                if latency < 0.5:
                    score += 15
                elif latency < 1:
                    score += 10
                elif latency < 2:
                    score += 5

        model = self.models.get(provider.name)

        if model:

            cost = model.get("cost", 5)

            score += max(0, 5 - cost)

        return max(score, 0)

    def rank(self, providers):

        return sorted(
            providers,
            key=self.score,
            reverse=True,
        )
