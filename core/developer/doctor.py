"""
Kaivor Developer Doctor
"""

from pathlib import Path


class DeveloperDoctor:
    """Basic project health checks."""

    def run(self):

        root = Path.cwd()

        print()
        print("=" * 60)
        print("KAIVOR DOCTOR")
        print("=" * 60)
        print()

        checks = {
            "core": root / "core",
            "knowledge": root / "knowledge",
            "workspace": root / "workspace",
            "tools": root / "tools",
            "kaivor.py": root / "kaivor.py",
        }

        passed = 0

        for name, path in checks.items():

            if path.exists():
                print(f"✓ {name}")
                passed += 1
            else:
                print(f"✗ {name}")

        print()
        print(f"{passed}/{len(checks)} checks passed")
        print()
