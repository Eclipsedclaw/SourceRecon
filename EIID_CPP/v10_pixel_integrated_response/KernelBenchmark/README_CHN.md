# KernelBenchmark——开发者说明

```text
KernelBenchmark/
├── config/benchmark_config.json  四份重建结果、真值和输出
├── include/BenchmarkConfig.h
├── include/BenchmarkRunner.h
├── src/                          ROOT 读取、指标、叠图和入口
├── Makefile                      生成 kernel_benchmark
├── README.md / README_CHN.md
└── MANUAL.md / MANUAL_CHN.md
```

类名沿用历史的 KernelBenchmark，但 V10 的正式用途是比较像素中心、两种父网格分辨率以及 i10/i20。四组均使用同一个 `gaussian_lorentzian_mixture` 响应核，因此观测到的差异来自像素积分与迭代设置，而不是响应模型更换。

程序读取每份 `EiidImage`，统一计算峰值角误差、峰值能量残差、边缘能谱均值/宽度、R50/R68/R90，并生成归一化能谱与方向包含率叠图。标定 held-out NLL/AIC/BIC 仍写入摘要，用于证明四组使用的是同一可用响应模型，不应将重复的标定分数误解为四次独立拟合。
