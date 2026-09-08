"""
Kaivor Diagnostics
"""

import importlib

from core.version import Version


class Diagnostics:
    """Runs basic system diagnostics."""

    REQUIRED_MODULES = (
        "requests",
        "feedparser",
        "pypdf",
        "docx",
    )

    def run(self):
        """Run diagnostics."""

        print()

        print("=" * 40)
        print(Version.full())
        print("=" * 40)

        print()

        print("Checking modules...")

        failures = []

        for module in self.REQUIRED_MODULES:

            try:

                importlib.import_module(module)

                print(f"✓ {module}")

            except ImportError:

                failures.append(module)

                print(f"✗ {module}")

        print()

        if failures:

            print("Missing modules:")

            for module in failures:
                print(f" - {module}")

            return False

        print("System diagnostics passed.")

        return True
