# EIID V7 模型无关质量指标架构——开发者说明

## 1. 项目目标

V7 是一套用于康普顿相机方向—能量联合重建的模块化 C++20 流水线。模拟、原始数据翻译、网格转换、重建和可视化都可以独立编译。

V7 完整继承 V5 的 Jeffreys 正则化绝对效率和 `绝对效率 × 条件事件响应` LM-MLEM 核心，不改变重建物理逻辑。本版只扩展可视化：以直接 FWHM、最短强度区间、方向加权质心/协方差和 R50/R68/R90 为主指标。Gaussian 仅作为可关闭的诊断插件。V5、V6 目录保持不变，可用于逐项对照。

源方向球面和重建方向网格统一以 ch2 几何中心为参考点。重建响应使用 `r2 - r1` 和入射单位方向，因此仍然具有平移不变性。

## 2. 总体架构

```text
v7_model_independent_metrics/
├── common/                 公共数据模型与 HEALPix 网格库
├── Reconstruction/         EIID 响应与 LM-MLEM 重建
├── GridResampler/          独立的绝对效率网格兼容器
├── Geant4_Simulation/      双模式探测器模拟程序
├── Translator/             Geant4 Step → 精简 Event 的 ETL 工具
├── Visualization/          独立 ROOT 绘图程序
├── legacy_v3_snapshot/     继承自 V3 的只读审计快照
├── Makefile                总编译入口
├── README.md               英文开发者文档
├── MANUAL.md               英文用户手册
├── README_CHN.md           中文开发者文档
└── MANUAL_CHN.md           中文用户手册
```

数据依赖关系：

```text
Geant4 Mode 0 ──> absolute_efficiency_master.root
                              │
                              v
                       GridResampler
                              │
                              v
                       absolute_efficiency.root
                              │
events.root ──────────────────┼──> Reconstruction ──> result.root
                                                            │
                                                            v
                                                     Visualization

raw_steps.root ──> Translator ──> events.root
Geant4 Mode 1 ─────────────────> events.root
```

算法模块不会通过隐藏的 ROOT 全局状态依赖某个具体读取器。每个 `main.cpp` 都明确构造配置和数据对象，再通过构造函数注入依赖。

## 3. common 公共库

`common/` 生成 `libeiid_common.a`，不包含 ROOT 或 Geant4 代码。

- `Common.h`：统一 `Decimal`、圆周率和电子静止质量。
- `PhysicsTypes.h`：`Vec3`、精简 `Event` 和方向—能量 `Cell`。
- `IGrid.h`：供求解器和网格兼容器使用的抽象网格接口。
- `HealpixGrid.h/.cpp`：RING 排序 HEALPix 方向网格和线性能量网格。
- `AbsoluteEfficiencyMap.h/.cpp`：连续的一维方向 × 能量存储，提供 O(1) 查询、重复检测、数值范围和完整性检查。
- `EfficiencyFileSchema.h`：效率 ROOT 文件的统一 Branch 与元数据名称。

网格插件接口是 `IGrid`。未来可替换网格实现，而不修改 LM-MLEM。

## 4. Reconstruction 重建模块

生成 `EIID_Recon_V7`。

- `ReconConfig`：解析和验证 `config/recon_config.json`，相对路径以 JSON 所在目录为基准。
- `IReconstructionSolver`：求解器接口。
- `LmMlemSolver`：当前列表模式 MLEM；正向预测显式包含绝对效率，真正位于模拟域外的零效率单元保持屏蔽。
- `EiidResponse`：康普顿能量与几何一致性响应。
- `RootEventReader`：只读取 `r1`、`r2`、`e1`，不包含 Step 聚合。
- `RootEfficiencyReader`：读取最小效率 Tree，并严格验证网格与物理元数据。
- `RootImageWriter`：写出可独立绘图的方向—能量结果。
- `main.cpp`：组合根，负责连接配置、网格、读取器、求解器和写入器。

求解器依赖 `IGrid` 和 `AbsoluteEfficiencyMap`，不依赖模拟器类。

## 5. GridResampler 网格兼容器

生成 `grid_resampler`。

- `ResamplerConfig`：Master/Target 网格、路径和插值选择。
- `IInterpolationStrategy`：插值插件接口。
- `NearestInterpolation`：方向和能量最近点插值。
- `PolygonInterpolation`：公共 HEALPix 细分，以微像素数量估算球面相交面积，再在能量轴上线性插值。
- `GridAdapter`：持有 Master/Target 网格，并选择策略。
- `ResamplerIO`：读写相同的最小绝对效率格式，并保留源半径。
- `resampler_main.cpp`：独立组合入口。

新增策略只需实现 `IInterpolationStrategy`，并在 `GridAdapter` 的工厂分支中注册。

## 6. Geant4_Simulation 模拟模块

生成 `geant4_simulator`。

### 几何和点源服务

- `DetectorConstruction`：探测器几何，以及自动计算尺寸和材料的 World。
- `DetectorGeometryInfo`：ch2 中心、触发包围盒和探测器边界的唯一数据源。
- `ISourceGeometry`：源位置插件接口。
- `Ch2CenteredHemisphereSource`：把每个点源放在

  \[
  \vec r_{source,j}=\vec r_{ch2}+R\vec n_j.
  \]

- `IEmissionConePolicy`：定向重要性采样接口。
- `AutoBoundingConePolicy`：锥轴指向 ch2 中心，半角覆盖 ch2+ch1 触发包围盒，再加安全余量。
- `AbsoluteEfficiencyEstimator`：把锥内触发计数转换为各向同性 (4\pi) 绝对概率。对每个实际参与模拟的 cell 使用 Jeffreys 平滑：

  \[
  \varepsilon_j=
  \frac{N_{valid,j}+\tfrac12}{N_{cone,j}+1}
  \frac{1-\cos\alpha_j}{2}.
  \]

  `N_cone = 0` 表示该 cell 不属于模拟域，效率仍严格为零。随着 `N_cone` 增大，上式自动收敛到原来的 `N_valid/N_cone` 估计。

### Geant4 Action 与 I/O

- `SimulationGrid`：将 Geant4 `eventID` 映射为 HEALPix 方向—能量单元。
- `PrimaryGeneratorAction`：使用注入的源与锥策略，并在锥内按立体角均匀采样。
- `EventAction`：能量加权 hit 聚合与 ch2+ch1 触发判定。
- `RunAction`：维护计数器，并将输出交给 `RootWriter`。
- `RootWriter`：Mode 0 写绝对效率；Mode 1 写精简触发事件。
- `TrackerHit/TrackerSD`、`MyPhysicsList` 和 Messenger：Geant4 探测器支撑代码。
- `main.cpp`：创建并注入所有服务。

源位置、发射锥和绝对效率归一化是三个独立组件，可以分别替换。

## 7. Translator 翻译模块

生成 `eiid_translator`。

- `IoConfig`：配置 JSON 路径、Branch、chamber 编号与阈值。
- `root_simulation_translator`：按 `eventID` 流式分组；同层正能量 Step 通过能量加权质心合并。
- 触发要求 ch2（`chamberID 0`）和 ch1（`chamberID 1`）均有沉积。
- 输出顺序固定为 `r1/e1 = ch2`、`r2 = ch1`。
- `translate_main.cpp`：独立入口。

若 Geant4 Mode 1 已直接生成精简事件，可跳过 Translator。

## 8. Visualization 可视化模块

生成 `eiid_plotter`，保留 Plotter 多态体系。

- `IPlotter`：绘图插件接口。
- `SkymapPlotter`：相机正前方 `-Z` 位于中心的全天球热力图。
- `SpectrumPlotter`：对方向求和后的能谱。
- `ContainmentPlotter`：累计方向包含率及 R50/R68/R90。
- `QualityAnalyzer`：共享的模型无关质量分析服务；找峰不使用真值。
- `EnergyMetricsPlotter`：方向门控能谱、直接 FWHM、最短强度区间和累计强度。
- `DirectionMetricsPlotter`：能量门控方向图、加权质心和 1/2 RMS 协方差椭圆。
- `EnergyAnglePlotter`：能量—相对真值角距离联合强度图。
- `QualitySummaryWriter`：输出 `quality_summary.json`，便于批量比较。
- `VisConfig`：绘图和真值 JSON 读取器。
- `ReconstructionDataReader`：一次读取 `result.root`，供所有图共用。
- `PlotUtils`：坐标和分箱工具。
- `vis_main.cpp`：根据 JSON 开关选择 Plotter。

方向不分别处理 theta/phi，而是在数据峰附近的球面切平面中求质心和协方差。MLEM 权重彼此相关，因此所有宽度均是描述性质量指标，不是严格置信区间；程序会把小于 HEALPix 像素尺度的方向宽度标记为分辨不足。Gaussian 失败不会影响主指标。

## 9. ROOT 数据格式

### 绝对效率文件

默认 Tree 为 `AbsoluteEfficiency`，包含：

- `cell_index`（`ULong64_t`）
- `efficiency`（`Double_t`）

文件级强制元数据：

- `healpix_nside`
- `healpix_ordering = RING`
- `direction_count`
- `energy_count`
- `energy_min_MeV`
- `energy_max_MeV`
- `source_radius_mm`
- `efficiency_definition = isotropic_point_source_absolute_detection_efficiency_4pi_jeffreys_regularized`

### 精简事件文件

默认 Tree 为 `Events`。Branch 包括 `eventID`、`r1_x/y/z`、`r2_x/y/z` 和 `e1_MeV`。Geant4 Mode 1 还会写 `source_cell_index`；Translator 不写该 Branch，因为重建不需要它。

### 重建结果

默认 Tree 为 `EiidImage`，保存单元索引、权重、HEALPix 像素编号、theta、phi、笛卡尔方向和能量。

## 10. 编译与扩展规则

每个顶层模块都有独立 `Makefile`，根 Makefile 只负责转发。进入任一模块即可单独编译，不必构建无关程序。Reconstruction 与 GridResampler 会在需要时自动生成 `common`。

扩展 V7 时必须遵守：

1. 依赖抽象接口，不依赖具体实现。
2. ROOT 所有权只能留在 I/O 类中。
3. Geant4 Action 不直接管理输出文件生命周期。
4. 用户路径以 JSON 文件位置为基准解析，而不是以终端当前目录为基准。
5. 数据格式或参数变化时，同时更新模块和根目录的中英文 README/MANUAL。
6. 网格元数据不一致时必须报错，不能静默接受。

`legacy_v3_snapshot/` 仅用于审计，不属于任何 V7 编译目标。

## 11. 机器依赖的一次性配置

`configure.sh` 是统一的依赖探测入口。它会从项目依赖前缀、常见环境目录、`PATH`、用户 HOME、`/opt` 和 `/usr/local` 中寻找 ROOT、HEALPix、nlohmann/json 及 Geant4。已知依赖环境的优先级高于 PATH，避免服务器上的不兼容 Snap ROOT 覆盖项目使用的 ROOT/HEALPix 环境。对于服务器共享的多个 Geant4，它会比较全部候选项，排除 `*-build` 构建目录，并自动选择版本号最高的正式安装版本；手动传入的 `ROOT_CONFIG` 和 `GEANT4_CONFIG` 始终优先。最后把绝对路径写入 `config/local.mk`。

所有模块 Makefile 都读取这个文件，不再依赖已经激活的 Conda 终端或隐式的 `CONDA_PREFIX`。链接阶段还会使用 `EIID_RPATH_FLAGS`，让可执行文件记住所需动态库目录。

`config/local.mk` 只适用于当前机器；迁移服务器后重新运行一次配置即可。`config/local.mk.example` 说明其格式。`PROJECT_CXX_STANDARD := c++20` 是唯一有效的语言标准设置；各模块会删除 ROOT 或 Geant4 自带的 `-std=...`，再把项目的 C++20 参数放在编译命令末尾，防止旧依赖偷偷把标准降级。依赖配置不会修改任何 C++ 源码、物理参数或 ROOT 数据格式。
