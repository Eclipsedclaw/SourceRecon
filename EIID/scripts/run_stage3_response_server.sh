#!/usr/bin/env bash
set -Eeuo pipefail

# 从脚本位置确定项目根目录，所有响应、日志和验证输出均留在 EIID 内。
SCRIPT_DIRECTORY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIRECTORY}/.." && pwd)"
PYTHON_EXECUTABLE="${EIID_PYTHON:-python}"
CONFIG_PATH="${EIID_CONFIG:-${PROJECT_ROOT}/config/examples/stage3_response_smoke.json}"
LOG_DIRECTORY="${EIID_LOG_DIRECTORY:-${PROJECT_ROOT}/logs}"

mkdir -p "${LOG_DIRECTORY}"
RUN_ID="${EIID_RUN_ID:-$("${PYTHON_EXECUTABLE}" "${PROJECT_ROOT}/scripts/generate_run_id.py" --kind stage3_response --config "${CONFIG_PATH}")}"
LOG_PATH="${EIID_LOG_PATH:-${LOG_DIRECTORY}/${RUN_ID}.log}"
export EIID_RUN_ID="${RUN_ID}"
export EIID_LOG_PATH="${LOG_PATH}"

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
echo "[EIID] run_id=${RUN_ID}"
echo "[EIID] log=${LOG_PATH}"
echo "[EIID] warning=stage3 response is synthetic prototype, not formal physics"

"${PYTHON_EXECUTABLE}" -u "${PROJECT_ROOT}/scripts/validate_stage3_response.py" --config "${CONFIG_PATH}" 2>&1 | tee -a "${LOG_PATH}"
