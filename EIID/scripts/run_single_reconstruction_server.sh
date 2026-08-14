#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIRECTORY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIRECTORY}/.." && pwd)"
PYTHON_EXECUTABLE="${EIID_PYTHON:-/home/ezqi/miniconda3/envs/py38/bin/python}"
: "${EIID_CONFIG:?请设置 EIID_CONFIG 为单数据集重建 JSON}"
CONFIG_PATH="${EIID_CONFIG}"
mkdir -p "${PROJECT_ROOT}/logs"
RUN_ID="${EIID_RUN_ID:-$("${PYTHON_EXECUTABLE}" "${PROJECT_ROOT}/scripts/generate_run_id.py" --kind production_reconstruction --config "${CONFIG_PATH}")}"
LOG_PATH="${EIID_LOG_PATH:-${PROJECT_ROOT}/logs/${RUN_ID}.log}"
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
EXTRA_ARGUMENTS=()
if [[ -n "${EIID_RESUME_FROM_RUN_ID:-}" ]]; then
  EXTRA_ARGUMENTS+=(--resume-from-run-id "${EIID_RESUME_FROM_RUN_ID}")
fi
"${PYTHON_EXECUTABLE}" -u "${PROJECT_ROOT}/main_experiment.py" \
  --config "${CONFIG_PATH}" "${EXTRA_ARGUMENTS[@]}" \
  2>&1 | tee -a "${LOG_PATH}"
