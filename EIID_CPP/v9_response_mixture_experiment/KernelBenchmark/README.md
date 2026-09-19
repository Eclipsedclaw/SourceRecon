# KernelBenchmark — developer guide

```text
config/  result list and truth
include/ configuration and runner
src/     ROOT reading, metrics, figures, main
outputs are centralized under runs/latest/benchmark/
```

This read-only module compares reconstructed images and reads calibration metrics without refitting. It first consults `model_status.json` and excludes unusable models, even if stale result files exist. It combines held-out NLL and aggregate AIC/BIC from `model_comparison.json` with peak direction/energy errors, marginalized energy moments, and R50/R68/R90. With one usable model it reports absolute metrics without a cross-model comparison; with none it fails. It deliberately does not collapse metrics with different units into an arbitrary scalar score.
