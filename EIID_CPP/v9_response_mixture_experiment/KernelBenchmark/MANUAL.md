# KernelBenchmark — user manual

```text
KernelBenchmark/{config,include,src,output,figures}
└── kernel_benchmark
```

```bash
cd KernelBenchmark
make
./kernel_benchmark config/benchmark_config.json
```

The JSON lists candidate result files with labels, kernel types, and tree names, plus `model_status_json`, `calibration_comparison_json`, truth, output JSON, and figure paths. Unusable models are skipped automatically. The report combines held-out calibration likelihood with final reconstruction metrics without inventing a mixed-unit scalar score. Results must share events, efficiency, grid, and iteration settings for a fair comparison. Defaults are written under `runs/latest/benchmark/`.
