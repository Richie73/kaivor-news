#!/usr/bin/env python3
"""FP008 one-command validation for Kaivor."""
from __future__ import annotations
import compileall
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(cmd: list[str]) -> int:
    print("$", " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT).returncode

def main() -> int:
    print("Kaivor FP008 validation")
    print("=" * 24)

    if not compileall.compile_dir(str(ROOT / "core"), quiet=1):
        print("FAIL: core compile")
        return 1
    if not compileall.compile_dir(str(ROOT / "commands"), quiet=1):
        print("FAIL: commands compile")
        return 1

    state = json.loads((ROOT / "build_state.json").read_text(encoding="utf-8"))
    if state.get("version") != "0.9.63" or state.get("milestone") != "FP008":
        print("FAIL: build metadata")
        return 1

    rc = run([sys.executable, "tools/run_tests_fp008.py"])
    if rc != 0:
        print("FAIL: API tests")
        return rc

    print("PASS: FP008 validation")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
