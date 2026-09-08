
#!/usr/bin/env python3
"""Run FP009 provider-independence regression tests."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
tests = [
    "tests/test_api.py",
    "tests/test_api_fp008.py",
    "tests/test_provider_independence.py",
]

for test in tests:
    print(f"\n=== {test} ===")
    result = subprocess.run([sys.executable, test], cwd=ROOT)
    if result.returncode:
        raise SystemExit(result.returncode)

print("\nALL FP009 TESTS PASSED")
