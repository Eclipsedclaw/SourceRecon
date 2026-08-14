#!/usr/bin/env python3
"""读取离线 Geant4 数据并执行 EIID 重建；不会在迭代中启动 Geant4。"""

from __future__ import annotations

import argparse
import json
import os

from eiid.application import run_experiment


def main():
    parser = argparse.ArgumentParser(description="运行离线 Geant4 数据 EIID 重建。")
    parser.add_argument("--config", required=True)
    parser.add_argument("--resume-from-run-id")
    args = parser.parse_args()
    summary = run_experiment(
        args.config,
        run_id=os.environ.get("EIID_RUN_ID") or None,
        log_path=os.environ.get("EIID_LOG_PATH") or None,
        run_kind="geant4_offline_reconstruction",
        resume_from_run_id=args.resume_from_run_id or os.environ.get("EIID_RESUME_FROM_RUN_ID") or None,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
