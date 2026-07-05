"""
Kaivor Status
"""

from core.providers.manager import ProviderManager
from core.ai.wallet import AIWallet


def run():

    manager = ProviderManager()
    wallet = AIWallet()

    print("\n========== KAIVOR STATUS ==========\n")

    print("Providers")

    for provider, state in manager.health().items():

        icon = "✓" if state else "✗"

        print(f"  {icon} {provider}")

    print()

    summary = wallet.summary()

    print(f"Requests : {summary['requests']}")

    print("\nUsage")

    for provider, count in summary["providers"].items():

        print(f"  {provider:<12} {count}")

    print()
