# EIID V8 Doppler-response architecture — user manual

## Orientation and tree

This manual explains configuration, build, and operation. See `README.md` for implementation details.

```text
production: Geant4_Simulation -> GridResampler -> Reconstruction -> Visualization
event ETL:  raw steps -> Translator -> events.root
V8 study:   DopplerSampleGenerator -> ResponseCalibration -> two reconstructions
             -> KernelBenchmark
```

## Configure and build

```bash
cd ~/labwork/SourceRecon/EIID_CPP/v8_doppler_response
make configure
make show-config
make all
make test
```

The generated `config/local.mk` stores absolute ROOT, HEALPix, JSON, Geant4, compiler, and rpath settings. It is machine-specific.

Independent builds include `make simulation`, `resampler`, `translator`, `sample-generator`, `response-calibration`, `response-kernel`, `reconstruction`, `kernel-benchmark`, and `visualization`.

## Recommended response-model study

```bash
make run-sample-grid
make calibrate
make reconstruct-voigt
make reconstruct-double-gaussian
make benchmark
```

`make response-study` runs all five steps. It reuses the same existing `events.root` and `absolute_efficiency.root` for both reconstructions.

Quick single-energy samples are `make run-sample-livermore` and `make run-sample-free`.

The five default production samples share one source direction, and the default calibration uses one global `[0,180]` scatter-angle bin. The first table is consequently energy-dependent only. Before physics use, copy the sample JSON files and vary `source.theta_degree` and `source.phi_degree` for multi-direction closure tests.

Outputs:

```text
doppler_response.root
ResponseCalibration/output/model_comparison.json
ResponseCalibration/figures/*.png
result_voigt.root
result_double_gaussian.root
KernelBenchmark/output/kernel_benchmark.json
KernelBenchmark/figures/*.png
```

## New JSON settings

`DopplerSampleGenerator/config/*.json` controls experiment name, seed, event count, Compton model, atomic relaxation, gamma energy/direction, point-source distance from the ch2 center, emission-cone margin, World material/margin, chamber IDs, energy threshold, and ROOT/JSON outputs.

`ResponseCalibration/config/calibration_config.json` controls input files/tree/truth-or-detector level, output ROOT/tree/histogram/JSON/figure paths, scatter-angle edges, ARM range/bins, minimum training events, and held-out fraction.

`Reconstruction/config/recon_*.json` adds:

```json
"response_kernel": {
  "type": "fixed_gaussian | voigt | double_gaussian | histogram",
  "fixed_sigma_degree": 6.0,
  "calibration_file": "../../doppler_response.root",
  "parameter_tree": "ResponseParameters",
  "histogram_name": "EmpiricalDetectorArmPdf"
}
```

An old V7 configuration without this object remains a fixed-Gaussian run.

`KernelBenchmark/config/benchmark_config.json` controls the result list, labels, kernel names, truth JSON, summary JSON, and figure directory.

All relative paths are resolved from the JSON file containing them.

## Existing production commands

```bash
make run-simulation SIM_CONFIG=config/sim_config.json
./GridResampler/grid_resampler GridResampler/config/resampler_config.json
./Translator/eiid_translator Translator/config/translator_config.json
./Reconstruction/EIID_Recon_V8 Reconstruction/config/recon_config.json
make run-visualization
```

The detailed retained settings are documented in each module's MANUAL.

## Dependency overrides

Prefer rerunning configuration:

```bash
ROOT_CONFIG=/path/root-config \
GEANT4_CONFIG=/path/geant4-config \
EIID_DEPS_PREFIX=/path/prefix \
make configure
```

If manual editing is unavoidable, edit only `config/local.mk`: `CXX`, `PROJECT_CXX_STANDARD`, `ROOT_CONFIG`, `GEANT4_CONFIG`, `HEALPIX_CFLAGS`, `HEALPIX_LIBS`, `JSON_CFLAGS`, and `EIID_RPATH_FLAGS`.

Low-statistics calibration bins, incomplete rectangular parameter tables, nonconverged fits, grid mismatches, and missing input files fail with explicit messages rather than silent substitutions.
