#!/usr/bin/env python3
"""薄包装:给 HTML 打 GEO 可被引用度分。等价于 geo_cli.py score。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo_cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["score"] + sys.argv[1:]))
