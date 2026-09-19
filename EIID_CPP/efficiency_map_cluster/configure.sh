#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_dir"
mkdir -p "$project_dir/build"
# 失败的 CMake 也会留下 CMakeCache.txt，不能用它代表配置成功。
rm -f -- "$project_dir/build/configure.ok"
trap 'status=$?; if (( status != 0 )); then rm -f -- "$project_dir/build/configure.ok"; fi' EXIT
if [[ -f config/environment.sh ]]; then
    set +u
    source config/environment.sh
    set -u
fi
log_file="$project_dir/build/configure_$(date -u +%Y%m%dT%H%M%S)_$$.log"
echo "Configure log: $log_file"
cmake -S "$project_dir" -B "$project_dir/build" -DCMAKE_BUILD_TYPE=Release "$@" 2>&1 | tee "$log_file"
