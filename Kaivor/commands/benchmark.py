"""
Kaivor AI Benchmark
"""

import time

from core.providers.manager import ProviderManager


def run():

    manager = ProviderManager()

    print("\n========== KAIVOR BENCHMARK ==========\n")

    for name in manager.list():

        provider = manager.get(name)

        start = time.perf_counter()

        try:

            configured = provider.configured()

            elapsed = (time.perf_counter() - start) * 1000

            if configured:
                state = "Ready"
                icon = "✓"
            else:
                state = "Not Configured"
                icon = "✗"

        except Exception:

            elapsed = (time.perf_counter() - start) * 1000
            state = "Unavailable"
            icon = "!"

        print(
            f"{icon} "
            f"{name:<12} "
            f"{elapsed:7.2f} ms   "
            f"{state}"
        )

    print()
