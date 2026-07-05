"""
Kaivor Wallet Command
"""

from core.ai.wallet import AIWallet


def run():

    wallet = AIWallet()

    summary = wallet.summary()

    print("\n========== AI WALLET ==========\n")

    print(f"Total Requests : {summary['requests']}")

    print("\nProvider Usage")

    for provider, count in summary["providers"].items():
        print(f"  {provider:<12} {count}")

    print()
