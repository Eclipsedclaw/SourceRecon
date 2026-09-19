# Geant4_Simulation——开发者说明

这是一个可独立编译的 Geant4 程序，包含两种运行模式：绝对探测效率标定，以及直接生成精简事件。

## 对象边界

- `ConfigManager`：只负责读取和验证 JSON。
- `DetectorConstruction`：构造探测器，并自动计算 World 尺寸和材料。
- `DetectorGeometryInfo`：几何信息的唯一来源；统一提供 ch2 中心、触发包围盒角点和探测器边界。
- `ISourceGeometry` / `Ch2CenteredHemisphereSource`：源位置插件接口及以 ch2 为中心的半球点源实现。
- `IEmissionConePolicy` / `AutoBoundingConePolicy`：重要性采样插件接口及自动包围发射锥实现。
- `AbsoluteEfficiencyEstimator`：计算发射锥立体角占比，并归一化到 (4\pi) 各向同性发射。
- `SimulationGrid`：把 Geant4 `eventID` 映射到方向—能量单元。
- `PrimaryGeneratorAction`：使用注入的源位置和发射锥服务生成粒子。
- `EventAction`：聚合 hit，并执行 ch2+ch1 触发判定。
- `RunAction`：管理计数器生命周期，并把输出工作交给 `RootWriter`。
- `RootWriter`：唯一持有 ROOT 输出文件的类。
- `TrackerHit`、`TrackerSD`、`MyPhysicsList` 和探测器 Messenger：继承的 Geant4 支撑代码。
- `main.cpp`：构造服务并将其注入各个 Action。

## 物理坐标约定

HEALPix 向量 `n_j` 从 ch2 几何中心指向点源，中心入射射线方向为 `-n_j`。点源位置为：

```text
source_position = ch2_center + R * n_j
```

`AutoBoundingConePolicy` 计算能够包围 ch2 和 ch1 有效 YSO 层的轴对齐包围体。发射锥半角等于源位置到各角点的最大夹角，再加上配置的安全余量。锥内采样对立体角均匀。

Mode 0 中绝对探测效率为：

```text
absolute efficiency = valid / cone-emitted × (1 - cos(half-angle)) / 2
```

每个单元只保存 `cell_index` 与 `sensitivity`，网格和科学定义等元数据只在 ROOT 文件层级保存一次。

## 扩展接口

新源分布实现 `ISourceGeometry`，新的重要性采样方法实现 `IEmissionConePolicy`。两者都可在 `main.cpp` 注入，无需修改 Geant4 Action 或 ROOT 输出模块。

独立 Makefile 从 `../config/local.mk` 读取 ROOT、HEALPix、JSON、Geant4 和 rpath 配置。若机器没有 Geant4，`configure.sh` 仍可配置其他模块，只有本模块会报告缺失依赖。

对于服务器共享安装，配置器会比较 PATH、HOME、`/opt` 和 `/usr/local` 内的所有候选项，排除 CMake 的 `*-build` 目录，并自动选择版本号最高的正式 Geant4 安装。依赖自带的 `-std=...` 会被过滤，编译命令末尾只保留项目统一的 C++20 设置。
