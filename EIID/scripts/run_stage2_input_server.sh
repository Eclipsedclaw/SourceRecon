#!/usr/bin/env bash
set -Eeuo pipefail

# 脚本根据自身位置定位 EIID 根目录，避免依赖调用者当前工作目录。
SCRIPT_DIRECTORY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIRECTORY}/.." && pwd)"

# 服务器 Python、配置和日志目录均可由环境变量覆盖，不在代码中写死。
PYTHON_EXECUTABLE="${EIID_PYTHON:-python}"
CONFIG_PATH="${EIID_CONFIG:-${PROJECT_ROOT}/config/examples/experiment_delimited_smoke.json}"
LOG_DIRECTORY="${EIID_LOG_DIRECTORY:-${PROJECT_ROOT}/logs}"

# 代码仓库通常不会保存空目录，因此每次运行前必须主动创建日志目录。
mkdir -p "${LOG_DIRECTORY}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_PATH="${LOG_DIRECTORY}/stage2_input_${TIMESTAMP}.log"

# 每个 Python 进程仅使用一个数值库线程；数据集级并行由后续调度器管理。
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"
export VECLIB_MAXIMUM_THREADS="${VECLIB_MAXIMUM_THREADS:-1}"
export BLIS_NUM_THREADS="${BLIS_NUM_THREADS:-1}"

cd "${PROJECT_ROOT}"
echo "[EIID] project=${PROJECT_ROOT}"
echo "[EIID] python=${PYTHON_EXECUTABLE}"
echo "[EIID] config=${CONFIG_PATH}"
echo "[EIID] log=${LOG_PATH}"

"${PYTHON_EXECUTABLE}" -u \
  "${PROJECT_ROOT}/scripts/validate_stage2_input.py" \
  --config "${CONFIG_PATH}" \
  2>&1 | tee -a "${LOG_PATH}"
