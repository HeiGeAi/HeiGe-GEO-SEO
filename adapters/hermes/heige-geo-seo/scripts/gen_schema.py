#!/usr/bin/env python3
"""薄包装:生成 JSON-LD 结构化数据。等价于 geo_cli.py schema。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo_cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["schema"] + sys.argv[1:]))
