# common：开发说明

纯配置/计数与 ROOT 持久化的公共层。不包含 Geant4 物理过程，不画图。

```text
common/
├── include/SimulationConfig.h / ConfigManager.hh
├── include/TaskSpec.h / CellCounts.h / RootSchema.h
├── src/SimulationConfig.cpp / TaskSpec.cpp / CellCounts.cpp
├── io/RootCountsIO.cpp
└── CMakeLists.txt
```

- SimulationConfig：检查源、能量网格、ch2/ch1阈值，返回只读配置。ConfigManager.hh 是兼容旧几何接口的薄头文件。
- TaskSpec/Campaign：从冻结的 manifest 读取任务，验证全局事件范围无重叠、无缺失；生成分块文件名及身份信息。
- CellCounts：64位 emitted/valid/hit/front/rear 计数，安全相加与完整性检查。不按事件数量分配数组。
- RootCountsIO：写临时ROOT、读回校验、发布正式分块；输出完整天空的 RawEfficiency。重复写入被拒绝。
- eff_common 可独立编译而不需要 ROOT；eff_root_io 由使用它的 Simulation/Merger 按需编译。
- eff_root_io PUBLIC 依赖 TreePlayer 和 eff_runtime；三个 ROOT 消费者继承同一套库。实际链接/运行兼容检查在上级 cmake/CheckDependencies.cmake，不在物理函数里处理。
- 上游是 JSON/manifest，下游是 Simulation、Merger。改 ROOT 协议要同步两者和原 Quicklook。
