"""
Developer Snapshot Wrapper
"""

import subprocess
import sys
from pathlib import Path


class DeveloperSnapshot:
    """Runs the Kaivor snapshot utility."""

    def run(self):

        project = Path.cwd()

        script = project / "tools" / "snapshot.py"

        print()
        print("=" * 60)
        print("KAIVOR SNAPSHOT")
        print("=" * 60)
        print()

        if not script.exists():
            print("Snapshot utility not found.")
            print()
            return

        subprocess.run([sys.executable, str(script)])

        print()
