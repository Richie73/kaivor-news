"""
Kaivor Display Utilities
"""


def banner(title):

    print()
    print("=" * 60)
    print(title.center(60))
    print("=" * 60)
    print()


def section(title):

    print()
    print("-" * 60)
    print(title)
    print("-" * 60)


def success(message):

    print(f"✓ {message}")


def error(message):

    print(f"✗ {message}")
