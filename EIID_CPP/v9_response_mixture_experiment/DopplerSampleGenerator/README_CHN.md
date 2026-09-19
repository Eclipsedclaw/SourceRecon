# DopplerSampleGenerator——开发者说明

## 定位与目录

```text
DopplerSampleGenerator/
├── config/                       单能、物理模型和输出配置
├── include/
│   ├── ConfigManager.hh
│   ├── ExperimentPhysicsList.hh  free/Livermore/LowEP 插件
│   ├── FixedPointSourceAction.hh 点源和自动发射锥
│   ├── ExperimentEventAction.hh  escape-Compton 真值选择
│   ├── ExperimentRunAction.hh
│   ├── ExperimentRecord.hh
│   └── 探测器几何、SD、Hit 与策略接口
├── src/                           Geant4 实现和入口
├── io/ExperimentRootWriter.*      样本 ROOT 与摘要输出
├── output/                        运行生成（不入库）
├── Makefile
├── README.md / README_CHN.md      开发者文档
└── MANUAL.md / MANUAL_CHN.md      用户手册
```

该模块来自已验证的 `doppler_v7_experiment`，但在 V9 中成为正式上游。它要求第一次主光子离散相互作用位于 ch2，第二次有效相互作用位于 ch1；允许后续光子逃逸，不要求全能沉积。truth 与 detector 两套 ARM 同时写盘。

生成器只生产响应样本，不生产绝对效率图；正式效率仍由 `Geant4_Simulation` 负责。
