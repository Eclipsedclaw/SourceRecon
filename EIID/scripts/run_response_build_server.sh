#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIRECTORY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIRECTORY}/.." && pwd)"
PYTHON_EXECUTABLE="${EIID_PYTHON:-/home/ezqi/miniconda3/envs/py38/bin/python}"
: "${EIID_RESPONSE_BUILD_CONFIG:?请设置 EIID_RESPONSE_BUILD_CONFIG 为响应构建 JSON}"
CONFIG_PATH="${EIID_RESPONSE_BUILD_CONFIG}"
mkdir -p "${PROJECT_ROOT}/logs"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_PATH="${EIID_RESPONSE_BUILD_LOG:-${PROJECT_ROOT}/logs/${TIMESTAMP}_response_build.log}"

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"
export VECLIB_MAXIMUM_THREADS="${VECLIB_MAXIMUM_THREADS:-1}"
export BLIS_NUM_THREADS="${BLIS_NUM_THREADS:-1}"

cd "${PROJECT_ROOT}"
"${PYTHON_EXECUTABLE}" -u "${PROJECT_ROOT}/scripts/build_response_library.py" \
  --config "${CONFIG_PATH}" 2>&1 | tee -a "${LOG_PATH}"
