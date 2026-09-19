# EIID V10 — user manual

## Quick start

Place the externally supplied compact `events.root` in the V10 project root. The default workflow validates and reads it but never creates or overwrites it.

```bash
cd ~/labwork/SourceRecon/EIID_CPP/v10_pixel_integrated_response
make configure
make all
make test
make experiment
```

`make configure` writes machine-local dependency paths to `config/local.mk`. Repeat it after changing ROOT, HEALPix, Geant4 or the compiler. The full experiment is computationally expensive.

## Workflow

```text
external events.root ----------------------------------------+
Geant4 efficiency -> resample Nside 8/16/32 -----------------+-> four reconstructions
Livermore samples -> calibration -> selected response kernel -+       |
                                                          benchmark + plots
```

The expanded sequence is:

```bash
make validate-events
make prepare-run
make run-simulation
make run-resampler-all
make run-sample-grid
make calibrate
make reconstruct-pixel-study
make benchmark
make visualize-pixel-study
```

Previous `runs/latest` output is archived under `runs/archive/<timestamp>`. A configuration snapshot and external-event SHA-256 are recorded.

## Principal configuration

`Geant4_Simulation/config/sim_config.json` controls mode, seed, source particle, ch2-centred hemisphere radius, front-hemisphere switch, automatic cone margin, World settings, Master Nside, energy grid, particles per cell, trigger thresholds and output ROOT paths.

`GridResampler/config/resampler_*.json` controls Master/Target grids, input/output ROOT files, `nearest|polygon`, polygon refinement and full-coverage enforcement.

`DopplerSampleGenerator/config/livermore_*.json` controls calibration energies, statistics, source geometry, physics model and selection. `ResponseCalibration/config/calibration_config.json` controls samples, ARM ranges, angle bins, train/test statistics and outputs.

Each reconstruction JSON controls event/result/efficiency paths, parent Nside, energy grid, iterations, response kernel, numerical floor and ROOT branches. New V10 fields are:

```json
"pixel_integration": {
    "strategy": "healpix_subpixel",
    "integration_nside": 64
}
```

`pixel_center` requires equal parent and integration Nsides. `healpix_subpixel` requires a power-of-two refinement. Samples per parent equal the squared Nside ratio.

## Reconstruction commands

```bash
make reconstruct-center          # Nside 8 centre, 10 iterations
make reconstruct-integrated-16   # parent 16, integration 32, 10
make reconstruct-integrated-32   # parent 32, integration 64, 10
make reconstruct-iteration-20    # parent 32, integration 64, 20
make reconstruct-pixel-study     # all four, sequentially
```

Run an existing executable directly with:

```bash
./Reconstruction/EIID_Recon_V10 Reconstruction/config/recon_config.json
```

## Plotting

```bash
make benchmark
make visualize-pixel-study
./Visualization/eiid_plotter Visualization/config/plot_config.json
```

Visualization runs ROOT in batch mode. Plot JSON files control all plot/summary switches, truth information, interval fraction and diagnostic windows.

## Independent builds

Every module remains independently buildable:

```bash
make -C PixelIntegration
make -C Reconstruction
make -C GridResampler
make -C Geant4_Simulation
make -C Visualization
```

Use `make clean` globally or `make -C <module> clean` locally.

## Dependency overrides

Prefer regenerating the central configuration:

```bash
ROOT_CONFIG=/absolute/path/root-config \
GEANT4_CONFIG=/absolute/path/geant4-config \
EIID_DEPS_PREFIX=/prefix/containing/healpix \
make configure
make show-config
```

If manual editing is unavoidable, edit only `config/local.mk`: `CXX`, `PROJECT_CXX_STANDARD`, `ROOT_CONFIG`, `HEALPIX_CFLAGS`, `HEALPIX_LIBS`, `JSON_CFLAGS`, `GEANT4_CONFIG`, and `EIID_RPATH_FLAGS`. Do not duplicate paths across module Makefiles.

For detailed Chinese parameter tables and troubleshooting, see [MANUAL_CHN.md](MANUAL_CHN.md).
