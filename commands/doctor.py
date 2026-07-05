"""
Kaivor AI Doctor
"""

from core.providers.manager import ProviderManager


def run():

    manager = ProviderManager()

    print("\n========== KAIVOR AI DOCTOR ==========\n")

    health = manager.health()

    for provider, status in health.items():

        icon = "✓" if status else "✗"

        print(f"{icon} {provider}")

    print()
