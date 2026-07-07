"""
Kaivor Maintenance Tools
"""

from pathlib import Path
import shutil


def clean_pycache():

    print()
    print("=" * 50)
    print("      CLEAN __pycache__")
    print("=" * 50)
    print()

    removed = 0

    for folder in Path(".").rglob("__pycache__"):

        try:
            shutil.rmtree(folder)
            print(f"✓ Removed {folder}")
            removed += 1

        except Exception as error:
            print(f"✗ {folder}")
            print(error)

    print()
    print(f"Removed {removed} cache folder(s).")
    print()
