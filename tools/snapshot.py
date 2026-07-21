
#!/usr/bin/env python3
"""
Kaivor Developer Snapshot Utility

Creates a clean ZIP archive of the Kaivor project.
"""

from zipfile import ZIP_DEFLATED, ZipFile

from core.developer.constants import (
    PROJECT_ROOT,
    SNAPSHOT_FILE,
    IGNORE_DIRS,
    IGNORE_SUFFIXES,
    IGNORE_FILES,
)


def should_skip(path):

    if any(part in IGNORE_DIRS for part in path.parts):
        return True

    if path.suffix in IGNORE_SUFFIXES:
        return True

    if path.name in IGNORE_FILES:
        return True

    return False


def main():

    SNAPSHOT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if SNAPSHOT_FILE.exists():
        SNAPSHOT_FILE.unlink()

    file_count = 0

    with ZipFile(
        SNAPSHOT_FILE,
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

            file_count += 1

    size = round(
        SNAPSHOT_FILE.stat().st_size / 1024 / 1024,
        2,
    )

    print()
    print("=" * 55)
    print("KAIVOR SNAPSHOT")
    print("=" * 55)
    print(f"Files archived : {file_count}")
    print(f"Archive size   : {size} MB")
    print(f"Saved to       : {SNAPSHOT_FILE}")
    print("=" * 55)
    print()


if __name__ == "__main__":
    main()