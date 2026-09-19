# SimulationSupport——开发者说明

## 定位与目录

该模块是 Geant4 标定样本生产端和 ROOT 标定读取端之间的轻量数据契约，不包含 Geant4/ROOT 对象。

```text
SimulationSupport/
├── include/CalibrationSchema.h   Branch 与元数据常量
├── src/CalibrationSchema.cpp     schema 描述和版本文字
├── tests/test_calibration_schema.cpp
├── Makefile
├── README.md / README_CHN.md     开发者文档
└── MANUAL.md / MANUAL_CHN.md     用户手册
```

任何样本 Branch 改名必须先改此处，再同时重新编译生成器与标定器。该库只负责格式，不负责事例筛选或拟合。
