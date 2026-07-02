"""
Kaivor Backup Manager
"""

from pathlib import Path
import shutil

from modules.developer.time_utils import timestamp
from modules.developer.ui import (
    title,
    success,
    error,
    start_timer,
    end_timer,
)

BACKUP_ROOT = Path("backups")


def create_backup():

    start_timer()

    try:

        backup_name = timestamp()
        backup_dir = BACKUP_ROOT / backup_name

        backup_dir.mkdir(parents=True, exist_ok=True)

        title("CREATE BACKUP")

        folders = [
            "ai",
            "config",
            "core",
            "database",
            "docs",
            "feeds",
            "logs",
            "modules",
            "scripts",
            "tests",
        ]

        files = [
            "kaivor.py",
            "README.md",
        ]

        for folder in folders:

            source = Path(folder)

            if source.exists():

                shutil.copytree(
                    source,
                    backup_dir / folder,
                    dirs_exist_ok=True,
                )

                success(folder)

        for file in files:

            source = Path(file)

            if source.exists():

                shutil.copy2(
                    source,
                    backup_dir / file,
                )

                success(file)

        print()
        success(f"Backup created: {backup_dir}")

    except Exception as e:

        error(str(e))

    finally:

        end_timer()