"""
Kaivor Provider Scoring
"""

from core.ai.provider_stats import ProviderStats


class ProviderScorer:
    """Scores AI providers."""

    def __init__(self):
        self.stats = ProviderStats()

    def score(self, provider):

        score = 0

        try:
            if provider.configured():
                score += 100

        except Exception:
            return 0

        stat = self.stats.summary().get(provider.name)

        if stat:

            score += stat["success"] * 2
            score -= stat["failure"] * 5

            latency = stat["average_latency"]

            if latency > 0:

                if latency < 0.5:
                    score += 15

                elif latency < 1:
                    score += 10

                elif latency < 2:
                    score += 5

        return max(score, 0)

    def rank(self, providers):
        """Return providers ordered by score."""

        ranked = sorted(
            providers,
            key=self.score,
            reverse=True,
        )

        return ranked
