"""
Kaivor Dependency Checker
"""

import importlib


class DependencyChecker:
    """Checks whether required Python modules exist."""

    REQUIRED = (
        "requests",
        "feedparser",
        "pypdf",
        "docx",
        "lxml",
    )

    def check(self):
        """Return missing dependencies."""

        missing = []

        for module in self.REQUIRED:

            try:
                importlib.import_module(module)

            except ImportError:
                missing.append(module)

        return missing

    def healthy(self):
        """Return True when all dependencies exist."""

        return len(self.check()) == 0
