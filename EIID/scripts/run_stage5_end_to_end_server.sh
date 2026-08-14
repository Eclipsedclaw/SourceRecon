#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIRECTORY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIRECTORY}/.." && pwd)"
PYTHON_EXECUTABLE="${EIID_PYTHON:-python}"
CONFIG_PATH="${EIID_CONFIG:-${PROJECT_ROOT}/config/examples/stage5_end_to_end_smoke.json}"
LOG_DIRECTORY="${EIID_LOG_DIRECTORY:-${PROJECT_ROOT}/logs}"

mkdir -p "${LOG_DIRECTORY}"
RUN_ID="${EIID_RUN_ID:-$("${PYTHON_EXECUTABLE}" "${PROJECT_ROOT}/scripts/generate_run_id.py" --kind experiment_reconstruction --config "${CONFIG_PATH}")}"
LOG_PATH="${EIID_LOG_PATH:-${LOG_DIRECTORY}/${RUN_ID}.log}"
export EIID_RUN_ID="${RUN_ID}"
export EIID_LOG_PATH="${LOG_PATH}"

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"
export VECLIB_MAXIMUM_THREADS="${VECLIB_MAXIMUM_THREADS:-1}"
export BLIS_NUM_THREADS="${BLIS_NUM_THREADS:-1}"
export MPLBACKEND="${MPLBACKEND:-Agg}"

cd "${PROJECT_ROOT}"
echo "[EIID] project=${PROJECT_ROOT}"
echo "[EIID] python=${PYTHON_EXECUTABLE}"
echo "[EIID] config=${CONFIG_PATH}"
echo "[EIID] run_id=${RUN_ID}"
echo "[EIID] log=${LOG_PATH}"
echo "[EIID] warning=stage5 analytic response is prototype, not formal physics"

"${PYTHON_EXECUTABLE}" -u "${PROJECT_ROOT}/main_experiment.py" --config "${CONFIG_PATH}" 2>&1 | tee -a "${LOG_PATH}"
