# Geant4_Simulation——开发者说明

2026-09-13：粒子源以独立标志明确覆盖默认 geantino，并打印实际粒子；
RunAction 增加命中/层阈值/触发摘要；TrackerSD 保留运输步骤中的正能量沉积。
`config/smoke_config.json` 与 `tests/check_smoke_output.C` 提供 28 万事例的
单能验证。完整说明及命令见实验根目录的 `README_CHN.md` 和 `MANUAL_CHN.md`。

```text
Geant4_Simulation/
├── config/   模式、源、网格、触发和输出
├── include/  几何、策略、Action、效率估计器
├── src/      Geant4 实现与入口
├── io/       效率和事件 ROOT 写出
├── tests/    绝对效率测试
├── Makefile
├── README.md / README_CHN.md
└── MANUAL.md / MANUAL_CHN.md
```

这是一个可独立编译的 Geant4 程序，包含两种运行模式：绝对探测效率标定，以及直接生成精简事件。

## 对象边界

- `ConfigManager`：只负责读取和验证 JSON。
- `DetectorConstruction`：构造探测器，并自动计算 World 尺寸和材料。
- `DetectorGeometryInfo`：几何信息的唯一来源；统一提供 ch2 中心、触发包围盒角点和探测器边界。
- `ISourceGeometry` / `Ch2CenteredHemisphereSource`：源位置插件接口及以 ch2 为中心的半球点源实现。
- `IEmissionConePolicy` / `AutoBoundingConePolicy`：重要性采样插件接口及自动包围发射锥实现。
- `AbsoluteEfficiencyEstimator`：同时计算未平滑的 `k/N` 估计和仅供对照的 Jeffreys 估计，再归一化到 (4\pi) 各向同性发射。
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
raw absolute efficiency = valid / cone-emitted
                          × (1 - cos(half-angle)) / 2
```

本实验的主 `efficiency` 分支不使用伪计数，因此 `valid = 0` 时严格为零。`regularized_efficiency` 只用于与旧公式比较。

每个单元保存 `cell_index`、raw `efficiency`、`regularized_efficiency`、`emitted_count`、`valid_count` 和 `cone_solid_angle_fraction`，用于诊断零计数问题。

## 扩展接口

新源分布实现 `ISourceGeometry`，新的重要性采样方法实现 `IEmissionConePolicy`。两者都可在 `main.cpp` 注入，无需修改 Geant4 Action 或 ROOT 输出模块。

独立 Makefile 从 `../config/local.mk` 读取 ROOT、HEALPix、JSON、Geant4 和 rpath 配置。若机器没有 Geant4，`configure.sh` 仍可配置其他模块，只有本模块会报告缺失依赖。

对于服务器共享安装，配置器会比较 PATH、HOME、`/opt` 和 `/usr/local` 内的所有候选项，排除 CMake 的 `*-build` 目录，并自动选择版本号最高的正式 Geant4 安装。依赖自带的 `-std=...` 会被过滤，编译命令末尾只保留项目统一的 C++20 设置。
