# KernelBenchmark — developer guide

```text
KernelBenchmark/{config,include,src} -> kernel_benchmark
```

The historical module name remains, but the V10 configuration compares four pixel-response settings that all use the same Gaussian-Lorentzian-mixture kernel. It reports peak direction/energy errors, marginal energy moments and R50/R68/R90, then draws normalized spectrum and containment overlays. Repeated calibration scores document the common upstream kernel; they are not independent fits.
