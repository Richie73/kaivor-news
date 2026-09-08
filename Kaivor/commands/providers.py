"""
Kaivor Provider Discovery
"""

from core.providers.manager import ProviderManager
from core.ai.scoring import ProviderScorer


def run():

    manager = ProviderManager()
    scorer = ProviderScorer()

    print("\n========== AI PROVIDERS ==========\n")

    providers = [
        manager.get(name)
        for name in manager.list()
    ]

    ranked = scorer.rank(providers)

    for provider in ranked:

        try:
            configured = provider.configured()
        except Exception:
            configured = False

        status = "✓" if configured else "✗"
        score = scorer.score(provider)

        print(
            f"{status} "
            f"{provider.name:<12} "
            f"Score: {score}"
        )

    print()
