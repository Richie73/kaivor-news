"""
Kaivor Capability Dashboard
"""

from core.ai.models import ModelRegistry
from core.ai.scoring import ProviderScorer
from core.providers.manager import ProviderManager


def run():

    manager = ProviderManager()
    models = ModelRegistry()
    scorer = ProviderScorer()

    print("\n========== AI CAPABILITIES ==========\n")

    for provider in scorer.rank(
        [manager.get(name) for name in manager.list()]
    ):

        info = models.get(provider.name)

        if info is None:
            continue

        try:
            status = "✓" if provider.configured() else "✗"
        except Exception:
            status = "!"

        print(
            f"{status} "
            f"{provider.name:<12} "
            f"Score: {scorer.score(provider)}"
        )

        capabilities = [
            key
            for key, value in info.items()
            if value is True
        ]

        print("   " + ", ".join(capabilities))
        print()
