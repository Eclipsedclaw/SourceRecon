# ResponseCalibration — user manual

```text
ResponseCalibration/{config,include,src,io,output,figures}
└── response_calibrator
```

```bash
cd ResponseCalibration
make
./response_calibrator config/calibration_config.json
```

Settings control input files/tree/truth-or-detector level/required Compton model, output ROOT/tree/histogram/JSON/figures, scatter-angle edges, ARM bins/range, minimum training and held-out statistics, and test fraction. Production reconstruction should use detector-level Livermore calibration and only converged, visually inspected bins.

The default `scatter_angle_edges_degree=[0,180]` intentionally fits one global ARM response per energy. The current ch2-to-ch1 geometry accepts predominantly forward scatters, so a separate mandatory `[90,180]` bin has no calibration events. Subdivide this axis only after the printed sample coverage and per-bin statistics demonstrate adequate support.
