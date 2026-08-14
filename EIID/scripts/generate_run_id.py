#!/usr/bin/env python3
"""为 Bash 包装器生成与配置快照绑定的 run_id；标准输出只包含编号。"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from eiid.application import RunIdFactory
from eiid.configuration import load_config


def main():
    parser = argparse.ArgumentParser(description="生成 EIID 唯一运行编号。")
    parser.add_argument("--kind", required=True)
    parser.add_argument("--config", required=True)
    arguments = parser.parse_args()
    config = load_config(arguments.config)
    print(RunIdFactory.generate(arguments.kind, config.as_dict()), flush=True)


if __name__ == "__main__":
    main()
