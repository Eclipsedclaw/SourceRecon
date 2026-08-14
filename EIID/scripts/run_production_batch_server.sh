#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIRECTORY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIRECTORY}/.." && pwd)"
PYTHON_EXECUTABLE="${EIID_PYTHON:-/home/ezqi/miniconda3/envs/py38/bin/python}"
BATCH_MANIFEST="${EIID_BATCH_MANIFEST:-${PROJECT_ROOT}/config/production/batch_manifest.json}"
LOG_DIRECTORY="${PROJECT_ROOT}/logs"
mkdir -p "${LOG_DIRECTORY}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_PATH="${EIID_BATCH_LOG:-${LOG_DIRECTORY}/${TIMESTAMP}_production_batch.log}"

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
echo "[EIID] batch_manifest=${BATCH_MANIFEST}"
echo "[EIID] log=${LOG_PATH}"

"${PYTHON_EXECUTABLE}" -u "${PROJECT_ROOT}/main_batch.py" \
  --manifest "${BATCH_MANIFEST}" \
  --python "${PYTHON_EXECUTABLE}" \
  2>&1 | tee -a "${LOG_PATH}"
