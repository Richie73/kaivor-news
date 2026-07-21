"""
Kaivor Developer Constants

Shared configuration for all developer tools.
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

DOWNLOADS = (
    Path.home()
    / "storage"
    / "downloads"
)

SNAPSHOT_FILE = DOWNLOADS / "Kaivor-latest.zip"


IGNORE_DIRS = {

    ".git",

    "__pycache__",

    ".pytest_cache",

    ".mypy_cache",

    ".venv",

    ".idea",

    ".vscode",

    "backups",

    "releases",

    "workspace",

    "logs",

    "output",

    "audit",

}


IGNORE_SUFFIXES = {

    ".pyc",

    ".pyo",

    ".log",

}


IGNORE_FILES = {

    "Kaivor-latest.zip",

}