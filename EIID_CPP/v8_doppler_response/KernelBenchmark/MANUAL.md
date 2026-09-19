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

The JSON lists two or more result files with labels, kernel types, and tree names, plus truth, output JSON, and figure paths. Results must share events, efficiency, grid, and iteration settings for a fair comparison.
