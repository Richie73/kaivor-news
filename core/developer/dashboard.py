"""
Developer Dashboard
"""

from pathlib import Path


class DeveloperDashboard:
    """Displays the Kaivor developer dashboard."""

    VERSION = "0.9.80"

    def show(self):

        project = Path.cwd().name

        print()
        print("=" * 60)
        print("KAIVOR DEVELOPER MODE")
        print("=" * 60)
        print()

        print(f"Project : {project}")
        print(f"Version : {self.VERSION}")

        print()

        print("Developer Utilities")
        print("-" * 60)

        utilities = [
            "doctor",
            "snapshot",
            "build",
            "test",
            "status",
            "commit",
            "push",
            "release",
        ]

        for utility in utilities:
            print(f"  • {utility}")

        print()
