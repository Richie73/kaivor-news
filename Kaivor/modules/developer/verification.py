"""
Kaivor Project Verification
"""

from pathlib import Path

from modules.developer.ui import (
    title,
    success,
    warning,
    error,
    start_timer,
    end_timer,
)


REQUIRED_FOLDERS = [
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

REQUIRED_FILES = [
    "kaivor.py",
    "README.md",
]


def verify_project():

    start_timer()

    title("PROJECT VERIFICATION")

    passed = 0
    failed = 0

    try:

        print("Folders")
        print("-" * 50)

        for folder in REQUIRED_FOLDERS:

            if Path(folder).exists():

                success(folder)
                passed += 1

            else:

                error(folder)
                failed += 1

        print()
        print("Files")
        print("-" * 50)

        for file in REQUIRED_FILES:

            if Path(file).exists():

                success(file)
                passed += 1

            else:

                error(file)
                failed += 1

        print()
        print("=" * 50)
        print(f"Passed : {passed}")
        print(f"Failed : {failed}")

        if failed == 0:

            success("Overall Status : HEALTHY")

        else:

            warning("Overall Status : ATTENTION REQUIRED")

    except Exception as e:

        error(str(e))

    finally:

        end_timer()