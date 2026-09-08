"""
Kaivor AI Analytics
"""

from core.ai.models import ModelRegistry
from core.ai.provider_stats import ProviderStats
from core.ai.scoring import ProviderScorer
from core.providers.manager import ProviderManager


def run():

    manager = ProviderManager()
    models = ModelRegistry()
    scorer = ProviderScorer()
    stats = ProviderStats()

    print("\n========== AI ANALYTICS ==========\n")

    summary = stats.summary()

    for provider in scorer.rank(
        [manager.get(name) for name in manager.list()]
    ):

        try:
            configured = provider.configured()
        except Exception:
            configured = False

        state = "✓" if configured else "✗"

        record = summary.get(
            provider.name,
            {
                "success": 0,
                "failure": 0,
                "average_latency": 0,
            },
        )

        print(
            f"{state} "
            f"{provider.name:<12}"
            f"Score:{scorer.score(provider):>4}   "
            f"Confidence:{scorer.confidence(provider):>5}%"
        )

        print(
            f"   Success : {record['success']}"
        )

        print(
            f"   Failure : {record['failure']}"
        )

        print(
            f"   Latency : {record['average_latency']} s"
        )

        recommended = []

        for capability in (
            "chat",
            "coding",
            "research",
            "writing",
            "vision",
        ):

            if models.supports(
                provider.name,
                capability,
            ):
                recommended.append(capability)

        print(
            "   Tasks   : "
            + ", ".join(recommended)
        )

        print()
