"""
Kaivor Model Registry
"""

from core.ai.models import ModelRegistry


def run():

    models = ModelRegistry()

    print("\n========== AI MODELS ==========\n")

    for provider, info in models.all().items():

        print(provider)

        for capability, value in info.items():
            print(f"  {capability:<14} {value}")

        print()
