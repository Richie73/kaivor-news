
#!/usr/bin/env python3
"""
Kaivor Automated Snapshot Pipeline
"""

import shutil
import time
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_FILE = (
    Path.home()
    / "storage"
    / "downloads"
    / "Kaivor-latest.zip"
)

EXCLUDED_DIRS = {
    "__pycache__",
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
    "backups",
    "releases",
    "logs",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".log",
}

EXCLUDED_FILES = {
    "Kaivor-latest.zip",
}


def should_skip(path: Path):

    if any(part in EXCLUDED_DIRS for part in path.parts):
        return True

    if path.suffix in EXCLUDED_SUFFIXES:
        return True

    if path.name in EXCLUDED_FILES:
        return True

    return False


def clean_project():

    removed = 0

    for directory in PROJECT_ROOT.rglob("__pycache__"):

        if directory.is_dir():
            shutil.rmtree(directory)
            removed += 1

    return removed


def create_snapshot():

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if OUTPUT_FILE.exists():
        OUTPUT_FILE.unlink()

    archived = 0

    with ZipFile(
        OUTPUT_FILE,
        "w",
        ZIP_DEFLATED,
    ) as archive:

        for item in PROJECT_ROOT.rglob("*"):

            if item.is_dir():
                continue

            if should_skip(item):
                continue

            archive.write(
                item,
                item.relative_to(PROJECT_ROOT),
            )

            archived += 1

    return archived


def main():

    start = time.time()

    print()
    print("=" * 60)
    print("KAIVOR SNAPSHOT PIPELINE")
    print("=" * 60)

    removed = clean_project()

    archived = create_snapshot()

    elapsed = round(time.time() - start, 2)

    size = round(
        OUTPUT_FILE.stat().st_size / 1024 / 1024,
        2,
    )

    print()
    print("Cleaning")
    print(f"  __pycache__ removed : {removed}")

    print()
    print("Snapshot")
    print(f"  Files archived      : {archived}")
    print(f"  Archive size        : {size} MB")

    print()
    print(f"Elapsed : {elapsed} seconds")

    print()
    print(f"Saved to:\n{OUTPUT_FILE}")

    print("=" * 60)
    print()


if __name__ == "__main__":
    main()