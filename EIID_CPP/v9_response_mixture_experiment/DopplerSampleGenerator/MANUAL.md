# DopplerSampleGenerator — user manual

```text
DopplerSampleGenerator/{config,include,src,io,output}
└── doppler_sample_generator
```

```bash
cd DopplerSampleGenerator
make
make run-free
make run-livermore
make run-calibration-grid
```

The grid target runs 0.3, 0.5, 0.662, 1.0, and 2.0 MeV Livermore configurations. These production samples are written to `runs/latest/calibration/samples/`; the external root-level `events.root` is never generated or overwritten. JSON settings control label, seed, event count, Compton model, atomic relaxation, point-source energy/direction/distance from ch2, cone margin, World, chamber thresholds, and output paths.

Use `make run-*` on shared servers so the matching Geant4 data environment is loaded automatically.
