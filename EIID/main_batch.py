#!/usr/bin/env python3
"""EIID 多数据集生产批处理入口。"""

from __future__ import annotations

import argparse
import json
import os

from eiid.batch import MemoryAwareBatchScheduler


def main():
    parser = argparse.ArgumentParser(description="运行 EIID 内存感知多数据集批处理。")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--python")
    args = parser.parse_args()
    summary = MemoryAwareBatchScheduler(
        args.manifest,
        python_executable=args.python or os.environ.get("EIID_PYTHON"),
    ).run()
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    if summary["status"] != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
