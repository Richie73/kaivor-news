"""
Kaivor System Information
"""

from config.version import VERSION, BUILD, STATUS
from core.providers.manager import ProviderManager


def run():

    manager = ProviderManager()

    print("\n========== KAIVOR SYSTEM ==========\n")

    print(f"Version : {VERSION}")
    print(f"Build   : {BUILD}")
    print(f"Status  : {STATUS}")

    print()

    print(f"Providers Registered : {len(manager.list())}")
    print(f"Providers Enabled    : {len(manager.enabled())}")

    print()
