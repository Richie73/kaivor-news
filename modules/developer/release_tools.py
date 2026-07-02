"""
Kaivor Release Builder
"""

from pathlib import Path
import shutil

from config.version import VERSION

from modules.developer.time_utils import timestamp
from modules.developer.ui import (
    title,
    success,
    error,
    start_timer,
    end_timer,
)


def build_release():

    start_timer()

    title("BUILD RELEASE")

    try:

        release_dir = Path("releases") / f"{VERSION}_{timestamp()}"

        release_dir.mkdir(parents=True, exist_ok=True)

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
                    release_dir / folder,
                    dirs_exist_ok=True,
                )

        for file in files:

            source = Path(file)

            if source.exists():

                shutil.copy2(
                    source,
                    release_dir / file,
                )

        print()
        success(f"Release created: {release_dir}")

    except Exception as e:

        error(str(e))

    finally:

        end_timer()