#!/usr/bin/env python3
"""EIID 实验数据端到端生产重建入口。"""

from __future__ import annotations

import argparse
import json
import os

from eiid.application import run_experiment


def main():
    parser = argparse.ArgumentParser(description="运行 EIID 实验数据联合重建。")
    parser.add_argument("--config", required=True)
    parser.add_argument("--resume-from-run-id")
    arguments = parser.parse_args()
    summary = run_experiment(
        arguments.config,
        run_id=os.environ.get("EIID_RUN_ID") or None,
        log_path=os.environ.get("EIID_LOG_PATH") or None,
        resume_from_run_id=(
            arguments.resume_from_run_id
            or os.environ.get("EIID_RESUME_FROM_RUN_ID")
            or None
        ),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
