"""
Kaivor Developer Status
"""

from pathlib import Path


class DeveloperStatus:
    """Display developer status."""

    def run(self):

        root = Path.cwd()

        print()
        print("=" * 60)
        print("KAIVOR STATUS")
        print("=" * 60)
        print()

        items = [
            ("Project", root.name),
            ("Core", "OK" if (root / "core").exists() else "Missing"),
            ("Knowledge", "OK" if (root / "knowledge").exists() else "Missing"),
            ("Workspace", "OK" if (root / "workspace").exists() else "Missing"),
            ("Developer", "OK" if (root / "core" / "developer").exists() else "Missing"),
            ("Tools", "OK" if (root / "tools").exists() else "Missing"),
        ]

        width = max(len(name) for name, _ in items)

        for name, value in items:
            print(f"{name:<{width}} : {value}")

        print()
