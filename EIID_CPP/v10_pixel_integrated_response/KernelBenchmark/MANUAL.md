# KernelBenchmark — user manual

Build and run with `make kernel-benchmark` followed by `make benchmark`, or invoke `./KernelBenchmark/kernel_benchmark KernelBenchmark/config/benchmark_config.json`.

Each `inputs[]` item defines a label, kernel type, result file and tree. Remaining fields select model/calibration status, common truth, output JSON and figure directory. The default compares all four V10 pixel-integration configurations under `runs/latest/benchmark/`.
