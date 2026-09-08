
"""
Kaivor Developer Dashboard
"""

from pathlib import Path
import subprocess

from config.version import VERSION
from modules.developer.ui import title, success, warning


def developer_dashboard():

    title("KAIVOR DEVELOPER CONSOLE")

    py_files = list(Path(".").rglob("*.py"))

    total_lines = 0

    for file in py_files:
        try:
            total_lines += sum(
                1 for _ in open(file, "r", encoding="utf-8")
            )
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

        git_clean = not result.stdout.strip()

    except Exception:

        git_clean = False

    if git_clean:
        success("Project Status : HEALTHY")
    else:
        warning("Project Status : MODIFIED")

    print(f"Version       : {VERSION}")
    print(f"Python Files  : {len(py_files)}")
    print(f"Project Lines : {total_lines}")
    print(f"Last Backup   : {last_backup}")
    print()

    print("1. System Diagnostics")
    print("2. Project Statistics")
    print("3. Verify Project")
    print("4. View Log File")
    print("5. Clear Log File")
    print("6. Git Status")
    print("7. Build Release")
    print("8. Clean __pycache__")
    print("9. Backup Project")
    print("10. Restore Backup")
    print("11. Memory Manager")
    print()
    print("0. Return")
    print()

