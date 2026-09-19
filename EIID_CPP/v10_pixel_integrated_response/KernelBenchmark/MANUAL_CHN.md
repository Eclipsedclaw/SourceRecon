# KernelBenchmark——用户手册

```bash
make kernel-benchmark
make benchmark
```

也可直接运行：

```bash
./KernelBenchmark/kernel_benchmark KernelBenchmark/config/benchmark_config.json
```

`inputs[]` 每项设置 `label`、`kernel_type`、结果 `file` 和 `tree`。其他参数指定模型状态 JSON、标定比较 JSON、统一真值、输出 JSON 和图片目录。默认比较四组 V10 重建，输出到 `runs/latest/benchmark/`。

运行前必须已经生成四份重建结果。比较时不要手工混入不同 `events.root`、能量网格或真值的结果。
