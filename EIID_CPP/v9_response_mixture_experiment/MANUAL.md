# EIID V9 response-model experiment — user manual

Place the externally supplied compact event file at `v9_response_mixture_experiment/events.root`, then run:

```bash
cd ~/labwork/SourceRecon/EIID_CPP/v9_response_mixture_experiment
make configure
make experiment
```

The `Events` tree must contain `Double_t` branches `r1_x`, `r1_y`, `r1_z`, `r2_x`, `r2_y`, `r2_z`, and `e1_MeV`. V9 validates but never generates or overwrites this external file.

The complete experiment archives an older `runs/latest`, regenerates the absolute-efficiency map, resamples it, generates five Doppler calibration samples, calibrates all three response models, reconstructs only models that converged in every required bin, benchmarks them, and creates per-model figures.

```bash
make all
make test
make validate-events
make prepare-run
make run-simulation
make run-resampler
make run-sample-grid
make calibrate
make reconstruct-eligible
make benchmark
make visualize-eligible
```

Important configuration files are:

- `Geant4_Simulation/config/sim_config.json`: source hemisphere, master HEALPix/energy grid, particles per cell, trigger, and efficiency output.
- `GridResampler/config/resampler_config.json`: master and target grids plus interpolation policy.
- `DopplerSampleGenerator/config/livermore_*.json`: calibration energies, source direction, event counts, seeds, and selection threshold.
- `ResponseCalibration/config/calibration_config.json`: ARM range/binning, angle bins, train/test requirements, and calibration outputs.
- `Reconstruction/config/recon_*.json`: external events, target grid, iterations, efficiency, kernel type, and ROOT branch mappings.
- `KernelBenchmark/config/benchmark_config.json`: candidate results, model-status and calibration-comparison files, truth, and output paths.
- `Visualization/config/truth_info.json` and `plot_*.json`: truth and plot switches.

`scatter_angle_bin_center_degree=90` labels the center of the current `[0,180]` bin; it does not claim that every event scattered at 90 degrees.

All generated products are under `runs/latest/`; previous runs are preserved under `runs/archive/`. `make clean` removes build products only, not event data or run results.
