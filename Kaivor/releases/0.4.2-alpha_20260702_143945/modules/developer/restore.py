"""
Kaivor Restore Manager
"""

from pathlib import Path
import shutil

from modules.developer.ui import (
    title,
    success,
    warning,
    error,
    start_timer,
    end_timer,
)

BACKUP_ROOT = Path("backups")


def restore_backup():

    start_timer()

    title("RESTORE BACKUP")

    try:

        if not BACKUP_ROOT.exists():

            warning("No backups found.")
            return

        backups = sorted(
            [b for b in BACKUP_ROOT.iterdir() if b.is_dir()],
            reverse=True,
        )

        if not backups:

            warning("No backups found.")
            return

        for i, backup in enumerate(backups, start=1):
            print(f"{i}. {backup.name}")

        print()

        choice = input("Restore which backup (0 to cancel): ").strip()

        if choice == "0":
            warning("Restore cancelled.")
            return

        try:
            backup = backups[int(choice) - 1]
        except (ValueError, IndexError):
            error("Invalid selection.")
            return

        confirm = input(
            "\nThis will overwrite project files. Continue? (y/N): "
        ).strip().lower()

        if confirm != "y":
            warning("Restore cancelled.")
            return

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

            source = backup / folder

            if source.exists():

                shutil.copytree(
                    source,
                    folder,
                    dirs_exist_ok=True,
                )

                success(folder)

        for file in files:

            source = backup / file

            if source.exists():

                shutil.copy2(
                    source,
                    file,
                )

                success(file)

        print()
        success("Restore completed successfully.")

    except Exception as e:

        error(str(e))

    finally:

        end_timer()