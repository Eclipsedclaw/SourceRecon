# ResponseCalibration — developer guide

```text
config/  calibration JSON
include/ config, fitter interface, three fitters, pipeline
src/     fitting and orchestration
io/      ROOT sample input
outputs are centralized under runs/latest/calibration/
```

The pipeline makes a deterministic event-ID train/test split per energy/scatter-angle bin. Voigt, double-Gaussian, and independent-width Gaussian-plus-Lorentzian mixture fit the same training histogram. AIC/BIC use training likelihood and held-out NLL uses test events. Fit status, covariance status, EDM, and call count are persisted with every fit.

`doppler_response.root` contains all parameterizations, `model_comparison.json` contains per-bin metrics, and `model_status.json` marks a model usable only when every required bin converged. The root workflow uses this file to exclude failed models from reconstruction and benchmarking.

The default uses one `[0,180]` scatter-angle interval because the present low-statistics ch2-to-ch1 sample cannot independently calibrate a backward-scatter bin. The angle coordinate remains in the table/interface for later high-statistics subdivision. Sparse ARM histograms are fitted with a Poisson binned likelihood.
