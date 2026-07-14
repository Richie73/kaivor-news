"""
Kaivor Build Manager
"""

import subprocess
import sys
from pathlib import Path


class BuildManager:
    """Compile every Python file."""

    def run(self):

        root = Path.cwd()

        print()
        print("=" * 60)
        print("KAIVOR BUILD")
        print("=" * 60)
        print()

        python_files = list(root.rglob("*.py"))

        failures = 0

        for file in python_files:

            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(file)],
                capture_output=True,
            )

            if result.returncode == 0:
                print(f"✓ {file.relative_to(root)}")
            else:
                failures += 1
                print(f"✗ {file.relative_to(root)}")

        print()
        print("-" * 60)

        if failures == 0:
            print(f"SUCCESS - {len(python_files)} files compiled.")
        else:
            print(f"FAILED - {failures} file(s) contain errors.")

        print()
