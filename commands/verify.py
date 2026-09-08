"""
Kaivor Verification Command
"""

from pathlib import Path
import importlib.util

from commands.test import run as run_tests


def module_exists(name):
    """Return True if a Python module is installed."""
    return importlib.util.find_spec(name) is not None


def count_documents(root):
    """Count supported knowledge documents."""

    counts = {
        ".txt": 0,
        ".docx": 0,
        ".pdf": 0,
    }

    root = Path(root)

    if not root.exists():
        return counts

    for file in root.rglob("*"):

        if not file.is_file():
            continue

        suffix = file.suffix.lower()

        if suffix in counts:
            counts[suffix] += 1

    return counts


def count_python_files(root):
    """Count Python source files."""

    root = Path(root)

    total = 0

    for file in root.rglob("*.py"):

        if ".git" in file.parts:
            continue

        if "__pycache__" in file.parts:
            continue

        total += 1

    return total


def run():
    """Run project verification."""

    print()
    print("=" * 60)
    print("KAIVOR PROJECT VERIFICATION")
    print("=" * 60)
    print()

    python_files = count_python_files(".")
    docs = count_documents("knowledge")

    print("Project")
    print(f"✓ Python files : {python_files}")
    print()

    print("Knowledge Library")
    print(f"✓ TXT   : {docs['.txt']}")
    print(f"✓ DOCX  : {docs['.docx']}")
    print(f"✓ PDF   : {docs['.pdf']}")
    print()

    print("Dependencies")

    dependencies = {
        "python-docx": module_exists("docx"),
        "pypdf": module_exists("pypdf"),
    }

    healthy = True

    for name, installed in dependencies.items():

        if installed:
            print(f"✓ {name}")
        else:
            print(f"✗ {name}")
            healthy = False

    print()
    print("Regression Tests")
    print()

    run_tests()

    print()
    print("=" * 60)

    if healthy:
        print("PROJECT STATUS : HEALTHY")
    else:
        print("PROJECT STATUS : ATTENTION REQUIRED")

    print("=" * 60)
