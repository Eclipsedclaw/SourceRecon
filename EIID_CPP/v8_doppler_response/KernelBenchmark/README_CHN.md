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
├── output/kernel_benchmark.json  运行生成
├── figures/                      能谱与包含率叠图
├── Makefile
├── README.md / README_CHN.md
└── MANUAL.md / MANUAL_CHN.md
```

该模块只读重建结果，不参与响应拟合。它对所有候选模型使用同一真值定义，比较峰值角误差、峰值能量误差、边缘能谱均值/宽度以及 R50/R68/R90。新增评价量只需修改 `BenchmarkRunner`，不会影响正式求解器。
