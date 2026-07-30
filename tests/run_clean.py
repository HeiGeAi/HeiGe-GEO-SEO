#!/usr/bin/env python3
"""Run the full unit suite and fail on leaked file handles."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    env = os.environ.copy()
    env["PYTHONTRACEMALLOC"] = "1"
    result = subprocess.run(
        [
            sys.executable,
            "-W",
            "always::ResourceWarning",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_*.py",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode:
        return result.returncode
    if "ResourceWarning" in result.stderr:
        print("ResourceWarning detected in unit suite", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
