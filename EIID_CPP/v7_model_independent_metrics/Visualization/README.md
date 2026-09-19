# Visualization — Developer README

Visualization is an independent ROOT executable that reads only `result.root` and truth JSON. V7 replaces fit-led reporting with model-independent image metrics while leaving reconstruction unchanged.

Core components:

- `IPlotter`: polymorphic plot interface.
- `VisConfig`: paths, switches, analysis settings, and truth.
- `ReconstructionDataReader`: one-time ROOT reader.
- `QualityAnalyzer`: interpolated energy peak, direct FWHM, shortest intensity interval, tangent-plane direction centroid/covariance, and containment.
- `EnergyMetricsPlotter`, `DirectionMetricsPlotter`, `EnergyAnglePlotter`: V7 diagnostics.
- `QualitySummaryWriter`: writes `quality_summary.json`.
- `vis_main.cpp`: composition root sharing one immutable `QualityAnalysisResult`.

Gaussian fits are optional diagnostics. Failure is reported as unavailable and never replaced by a moment estimate labelled as a fit. Primary metrics remain usable without Gaussian convergence.

MLEM weights are correlated and are not independent Poisson counts. Report widths as descriptive image metrics and keep R50/R68/R90 and the HEALPix pixel scale alongside them.

To add a plot, implement `IPlotter`, add the source under `src/`, and register it in `vis_main.cpp`.
