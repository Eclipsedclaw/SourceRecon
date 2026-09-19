# KernelBenchmark — developer guide

```text
config/  result list and truth
include/ configuration and runner
src/     ROOT reading, metrics, figures, main
output/  JSON metrics
figures/ spectrum and containment overlays
```

This read-only module compares reconstructed images, not calibration fits. It reports peak direction/energy errors, marginalized energy moments, and R50/R68/R90. New end-to-end metrics remain isolated from the solver.
