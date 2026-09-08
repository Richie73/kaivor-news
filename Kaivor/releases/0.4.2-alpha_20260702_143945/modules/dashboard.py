
"""
Kaivor Developer Dashboard
"""

from pathlib import Path
from config.version import VERSION
import subprocess


def developer_dashboard():

    py_files = len(list(Path(".").rglob("*.py")))

    total_lines = 0

    for file in Path(".").rglob("*.py"):

        try:
            with open(file, "r", encoding="utf-8") as f:
                total_lines += len(f.readlines())
        except Exception:
            pass

    backups = sorted(Path("backups").glob("*"))
    last_backup = backups[-1].name if backups else "None"

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
        )
        git_status = "Modified" if result.stdout.strip() else "Clean"
    except Exception:
        git_status = "Unavailable"

    status = "HEALTHY"

    if git_status == "Unavailable":
        status = "WARNING"

    print("=" * 50)
    print("       KAIVOR DEVELOPER CONSOLE")
    print("=" * 50)
    print()

    print(f"Project Status : {status}")
    print(f"Version        : {VERSION}")
    print(f"Git Status     : {git_status}")
    print(f"Python Files   : {py_files}")
    print(f"Project Lines  : {total_lines}")
    print(f"Last Backup    : {last_backup}")

    print()