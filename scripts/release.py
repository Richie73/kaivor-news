"""
Kaivor Release Builder
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pathlib import Path
from datetime import datetime

from config.version import VERSION


def create_release():

    release_dir = Path(f"releases/v{VERSION}")

    release_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%d %B %Y")

    readme = f"""# Kaivor {VERSION}

Release Date: {today}

## Overview

Kaivor is a modular AI-powered Personal Intelligence Platform.

This release was generated automatically.
"""

    changelog = f"""# Changelog

## {VERSION}

### Added

-

### Changed

-

### Fixed

-
"""

    install = """# Installation

git clone https://github.com/Richie73/Kaivor.git

pip install -r requirements.txt

python kaivor.py
"""

    (release_dir / "README.md").write_text(readme)

    (release_dir / "CHANGELOG.md").write_text(changelog)

    (release_dir / "INSTALL.md").write_text(install)

    print()
    print("=" * 50)
    print("Release created successfully")
    print("=" * 50)
    print()
    print(release_dir)


if __name__ == "__main__":
    create_release()
