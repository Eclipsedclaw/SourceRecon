#!/usr/bin/env bash
set -Eeuo pipefail

# 可由外部覆盖；脚本本身不固定服务器 Python 和项目位置。
SCRIPT_DIRECTORY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIRECTORY}/.." && pwd)"
PYTHON_EXECUTABLE="${EIID_PYTHON:-python}"
CONFIG_PATH="${EIID_CONFIG:-${PROJECT_ROOT}/config/examples/foundation_smoke.json}"
LOG_DIRECTORY="${EIID_LOG_DIRECTORY:-${PROJECT_ROOT}/logs}"

mkdir -p "${LOG_DIRECTORY}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_PATH="${LOG_DIRECTORY}/foundation_${TIMESTAMP}.log"

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
  "${PROJECT_ROOT}/scripts/validate_foundation.py" \
  --config "${CONFIG_PATH}" \
  2>&1 | tee -a "${LOG_PATH}"

