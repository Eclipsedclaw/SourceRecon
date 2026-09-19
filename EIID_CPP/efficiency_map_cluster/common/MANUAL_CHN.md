# common：操作说明

本模块没有独立物理模拟命令。整体流程是 JSON→common配置→Simulation分块→Merger→最终ROOT。

```text
common/
├── include/SimulationConfig.h / ConfigManager.hh
├── include/TaskSpec.h / CellCounts.h / RootSchema.h
├── src/SimulationConfig.cpp / TaskSpec.cpp / CellCounts.cpp
├── io/RootCountsIO.cpp
└── CMakeLists.txt
```

独立检查纯计数逻辑：

```bash
cmake -S common -B build-common
cmake --build build-common --parallel 4
ctest --test-dir build-common --output-on-failure
```

在项目根目录执行。此模式不需要 ROOT/Geant4；统一构建后的 make test 还会执行真实 ROOT I/O 往返测试。

common 接收 config/sim_config.json 和生成后的 manifest.json。用户只改前者，不手改 manifest。源半径/前半球/自动锥余量控制源几何，Nside和能量上下限/点数控制网格，particles_per_cell 控制统计量，ch2/ch1阈值控制接受事件。

所有字段的单位、约束和默认值见 [总体手册](../MANUAL_CHN.md#二可以调整哪些参数)。改物理或任务参数后用新批次目录，防止混合旧计数。

RawEfficiency中的 efficiency 是原始(k/N)*圆锥4π占比。emitted_count>0但valid_count=0并不是缺行，应保持零；emitted_count=0表示未模拟。不要在本模块加小正数“修复”零值。

