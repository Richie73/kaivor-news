#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys

PROJECT = Path("/storage/emulated/0/Download/KAIVOR/Kaivor").resolve()
NESTED = PROJECT / "Kaivor"

print("Kaivor FP008 cleanup")
print("====================")
print(f"Project: {PROJECT}")
print(f"Nested duplicate: {NESTED}")

if not PROJECT.is_dir():
    print("ERROR: Project directory not found.")
    sys.exit(1)

if not NESTED.exists():
    print("OK: No nested Kaivor directory exists.")
    sys.exit(0)

if not NESTED.is_dir():
    print("ERROR: Nested Kaivor path exists but is not a directory.")
    sys.exit(1)

# Safety check: only remove the exact accidental nested project directory.
if NESTED.parent != PROJECT:
    print("ERROR: Safety check failed.")
    sys.exit(1)

shutil.rmtree(NESTED)
print("OK: Removed accidental nested Kaivor directory.")
print("The root project remains untouched.")
