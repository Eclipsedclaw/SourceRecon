# ResponseCalibration — developer guide

```text
config/  calibration JSON
include/ config, sample reader, fitter interface, two fitters, pipeline
src/     fitting and orchestration
io/      ROOT sample input
output/  metric JSON
figures/ per-bin overlays
```

The pipeline makes a deterministic event-ID train/test split per energy/scatter-angle bin. Both models fit the same training histogram. AIC/BIC use training likelihood and held-out NLL uses test events. The ROOT output contains both parameterizations and a slice-normalized empirical TH3D.

The default uses one `[0,180]` scatter-angle interval because the present low-statistics ch2-to-ch1 sample cannot independently calibrate a backward-scatter bin. The angle coordinate remains in the table/interface for later high-statistics subdivision. Sparse ARM histograms are fitted with a Poisson binned likelihood.
