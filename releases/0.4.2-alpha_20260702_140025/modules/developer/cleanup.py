
"""
Kaivor Cache Cleaner
"""

from pathlib import Path
import shutil

from modules.developer.ui import (
    title,
    success,
    error,
    start_timer,
    end_timer,
)


def clean_pycache():

    start_timer()

    title("CLEAN __pycache__")

    removed = 0

    try:

        for folder in Path(".").rglob("__pycache__"):

            try:

                shutil.rmtree(folder)

                success(f"Removed {folder}")

                removed += 1

            except Exception:
                pass

        print()
        print(f"Removed {removed} cache folder(s).")

    except Exception as e:

        error(str(e))

    finally:

        end_timer()