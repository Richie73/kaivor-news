
"""
Kaivor Developer UI
"""

from time import perf_counter

_timer = None


def start_timer():
    global _timer
    _timer = perf_counter()


def end_timer():
    if _timer is None:
        return

    elapsed = perf_counter() - _timer

    print()
    print("-" * 50)
    print(f"Completed in {elapsed:.2f} seconds")
    print("-" * 50)


def title(text):
    print()
    print("=" * 50)
    print(text.center(50))
    print("=" * 50)
    print()


def success(message):
    print(f"✓ {message}")


def warning(message):
    print(f"! {message}")


def error(message):
    print(f"✗ {message}")


def divider():
    print("-" * 50)


def pause():
    input("\nPress Enter to continue...")
