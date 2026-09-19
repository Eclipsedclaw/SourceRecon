#!/usr/bin/env bash

set -euo pipefail

script_directory="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
project_root="$(cd "${script_directory}/.." && pwd -P)"
runs_root="${project_root}/runs"
latest="${runs_root}/latest"
expected_latest="${project_root}/runs/latest"

mkdir -p "${runs_root}/archive"

# This equality check makes the archive operation safe even if this script is
# edited later. Only the V10-generated runs/latest directory may be moved.
if [[ "${latest}" != "${expected_latest}" ]]; then
    echo "Error: refusing to prepare unexpected run directory: ${latest}" >&2
    exit 1
fi

if [[ -d "${latest}" ]]; then
    timestamp="$(date +%Y%m%d_%H%M%S)"
    archive="${runs_root}/archive/${timestamp}"

    if [[ -e "${archive}" ]]; then
        archive="${archive}_$$"
    fi

    mv -- "${latest}" "${archive}"
    echo "Previous run archived at ${archive}"
fi

mkdir -p \
    "${latest}/efficiency" \
    "${latest}/calibration/samples" \
    "${latest}/calibration/figures" \
    "${latest}/reconstruction" \
    "${latest}/benchmark/figures" \
    "${latest}/visualization" \
    "${latest}/config_snapshot"

cp -- "${project_root}/Geant4_Simulation/config/sim_config.json" \
    "${latest}/config_snapshot/"
cp -- "${project_root}/GridResampler/config/"*.json \
    "${latest}/config_snapshot/"
cp -- "${project_root}/ResponseCalibration/config/calibration_config.json" \
    "${latest}/config_snapshot/"
cp -- "${project_root}/DopplerSampleGenerator/config/"livermore_*.json \
    "${latest}/config_snapshot/"
cp -- "${project_root}/Reconstruction/config/"*.json \
    "${latest}/config_snapshot/"
cp -- "${project_root}/KernelBenchmark/config/benchmark_config.json" \
    "${latest}/config_snapshot/"
cp -- "${project_root}/Visualization/config/truth_info.json" \
    "${latest}/config_snapshot/"
cp -- "${project_root}/Visualization/config/"plot_*.json \
    "${latest}/config_snapshot/"

{
    echo "schema=eiid_v10_run_manifest"
    echo "created_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "external_events_file=${project_root}/events.root"

    if command -v sha256sum >/dev/null 2>&1; then
        event_hash="$(sha256sum "${project_root}/events.root" | awk '{print $1}')"
        echo "external_events_sha256=${event_hash}"
    fi
} > "${latest}/run_manifest.txt"

echo "Fresh V10 run directory prepared at ${latest}"
