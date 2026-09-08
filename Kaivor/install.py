import subprocess
import sys
import os

PACKAGES = [
    "feedparser",
    "requests",
    "python-dateutil"
]


def install(package):
    print(f"Installing {package}...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", package]
    )


def main():

    print("=" * 60)
    print("KAIVOR INSTALLER")
    print("=" * 60)
    print()

    for package in PACKAGES:
        try:
            __import__(package.replace("-", "_"))
            print(f"✓ {package} already installed")
        except ImportError:
            install(package)

    print()
    print("Installation complete.")
    print("Kaivor is ready.")


if __name__ == "__main__":
    main()