# KernelBenchmark——开发者说明

## 定位与目录

```text
KernelBenchmark/
├── config/benchmark_config.json
├── include/BenchmarkConfig.h
├── include/BenchmarkRunner.h
├── src/BenchmarkConfig.cpp
├── src/BenchmarkRunner.cpp
├── src/main.cpp
├── Makefile
├── README.md / README_CHN.md
└── MANUAL.md / MANUAL_CHN.md
```

该模块只读重建结果、`model_status.json` 和 `model_comparison.json`，不参与响应拟合。它先排除标定未通过的模型，再对其余候选使用同一真值定义，比较 held-out NLL、AIC/BIC、峰值角误差、峰值能量误差、边缘能谱均值/宽度以及 R50/R68/R90。

若至少两个模型可用，执行横向比较；若仅一个模型可用，仍输出其绝对指标，但明确设置 `multi_model_comparison_performed=false`；若没有可用模型则报错。程序不强行把不同单位的指标揉成一个主观总分，也不会因为目录中残留旧 ROOT 文件而把失败模型误纳入比较。

新增评价量只需修改 `BenchmarkRunner`，不会影响标定器和正式求解器。默认结果位于 `runs/latest/benchmark/`。
