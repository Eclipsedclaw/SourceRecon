#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
ROOT_PREFIX="${ROOT_PREFIX:-/home/ezqi/miniconda3/envs/root-env}"
test -x "$ROOT_PREFIX/bin/root" || { printf '%s\n' 'ROOT executable not found; set ROOT_PREFIX.' >&2; exit 1; }
export LD_LIBRARY_PATH="$ROOT_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
printf '%s  %s\n' '0f248e0141e753ac091514e3c633046cb20d564cca944e91854b5781793ae069' 'input/raw_efficiency_master.root' | sha256sum -c -
mkdir -p figures
"$ROOT_PREFIX/bin/root" -l -b -q run_efficiency_slice.C 2>&1 | tee figures/plot.log
