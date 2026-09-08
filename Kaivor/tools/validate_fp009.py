#!/usr/bin/env python3
"""One-command FP009 validation."""
from __future__ import annotations
import compileall
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(test):
    print("$", sys.executable, test)
    return subprocess.run([sys.executable, test], cwd=ROOT).returncode

def main():
    print("Kaivor FP009 validation")
    print("========================")

    for folder in ("core", "commands"):
        if not compileall.compile_dir(str(ROOT / folder), quiet=1):
            print(f"FAIL: {folder} compile")
            return 1

    state = json.loads((ROOT/"build_state.json").read_text())
    if state.get("version") != "0.9.64" or state.get("milestone") != "FP009":
        print("FAIL: build metadata")
        return 1

    for test in ("tests/test_api.py", "tests/test_openrouter_fp009.py"):
        rc = run(test)
        if rc:
            print(f"FAIL: {test}")
            return rc

    print("PASS: FP009 validation")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
