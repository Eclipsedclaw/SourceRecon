#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# 环境加载、Geant4/ROOT 的 stdout 和 stderr 都由 Python 同时写入终端和 .log。
exec "${EFF_PYTHON:-python3}" "$project_dir/cluster/workflow.py" "$@"
