# EIID V3 JSON Architecture

## 1. 文档状态与版本边界

本目录是 EIID 项目的 V3 独立工作区。它由上一版 `vis_module_version` 完整复制而来，历史版本不会在本目录的开发过程中被修改。

当前执行状态：

- 已完成：JSON 重建器、网格兼容器、Geant4 双模式模拟器、Translator JSON 配置化和根 Makefile。
- 保留可用：上一版可视化模块以及历史代码快照。
- 实现边界：V3 新代码只位于本目录，没有改写任何历史版本。

V3 重建源码统一放在 `src/`。复制基线中与 `Parameter` 相关的过渡副本已从本工作区移除；`io/` 仅保留独立 Translator 所需的文件。

---

## 2. 全局坐标与数据约定

全项目采用以下统一约定：

- HEALPix 编号方案：`RING`。
- `theta`：从全局 `+Z` 轴量起，范围为 `[0°, 180°]`。
- `phi`：绕 `Z` 轴的方位角，推荐归一化到 `[0°, 360°)`。
- Geant4 相机正前方：全局 `-Z`，即 `theta = 180°`。
- 能量单位：MeV。
- 位置单位：由 Geant4 几何统一规定；写入 ROOT 时必须在 Branch 名或元数据中注明。
- 联合网格的一维索引：

```text
flat_index = direction_index * energy_count + energy_index
```

该排列与当前 `Grid::cells()` 的“方向在外、能量在内”循环一致。

---

## 3. 子系统 1：全局 JSON 化与新版重建引擎

### 3.1 目标架构

```text
v3_json_architecture/
├── config/
│   ├── recon_config.json
│   ├── translator_config.json
│   └── 可视化配置保持上一版语义不变
├── include/
│   ├── ReconConfig.h
│   ├── SensitivityMatrix.h
│   ├── sensitivity_reader.h
│   └── 原有公共算法接口
├── src/
│   ├── core/
│   │   ├── eiid_core.cpp
│   │   ├── mlem_core.cpp
│   │   ├── ReconConfig.cpp
│   │   └── SensitivityMatrix.cpp
│   ├── io/
│   │   ├── data_input.cpp
│   │   ├── data_output.cpp
│   │   └── sensitivity_reader.cpp
│   └── main.cpp
└── vis/
    └── 上一版可视化模块原样保留
```

新重建器已废除对 `Parameter` 的依赖；`ReconConfig` 是 `EIID_Recon_V3` 唯一的运行参数入口。

### 3.2 `config/recon_config.json` 参数设计

| 参数 | 类型 | 意义 |
|---|---:|---|
| `input_events_file` | string | Translator 生成的精简事件 ROOT 文件路径。 |
| `input_events_tree` | string | 精简事件树名称，默认语义为 `Events`。 |
| `output_result_file` | string | 重建结果 ROOT 文件路径。 |
| `output_result_tree` | string | 重建联合图的 TTree 名称。 |
| `sensitivity_file` | string | 与目标重建网格一致的敏感度 ROOT 文件。 |
| `sensitivity_tree` | string | 敏感度树名称。 |
| `healpix_nside` | integer | 重建方向网格的 HEALPix Nside。必须为正，并建议使用 2 的整数次幂。 |
| `healpix_ordering` | string | HEALPix 编号方式；V3 基线固定为 `RING`。 |
| `energy_min_MeV` | number | 候选入射能量下界。 |
| `energy_max_MeV` | number | 候选入射能量上界。 |
| `energy_point_count` | integer | 包含上下边界在内的候选能量点数。 |
| `iteration_count` | integer | LM-MLEM 迭代次数。 |
| `response_sigma_degree` | number | 方向响应核的角宽度参数。 |
| `denominator_floor` | number | 防止浮点分母接近零的正数下限。 |
| `require_complete_sensitivity` | boolean | 是否要求敏感度矩阵覆盖全部方向－能量 cell。建议生产运行设为 `true`。 |
| `event_branches` | object | `r1_x/y/z`、`r2_x/y/z`、`e1_MeV` 等输入分支名。 |
| `result_branches` | object | `cell_index`、方向坐标、能量和 `weight` 等输出分支名。 |
| `sensitivity_branches` | object | 敏感度文件中的方向下标、能量下标、发射数、有效数和敏感度分支名。 |

所有相对路径都必须以 JSON 文件所在目录为基准解析，不能依赖启动程序时恰好位于哪个目录。

### 3.3 `config/translator_config.json` 参数设计

| 参数 | 类型 | 意义 |
|---|---:|---|
| `raw_input_file` | string | Geant4 原始 step 级 ROOT 文件。 |
| `raw_input_tree` | string | 原始 step 树名称。 |
| `output_events_file` | string | Translator 输出的精简事件文件。 |
| `output_events_tree` | string | 精简事件树名称。 |
| `front_chamber_id` | integer | 最前方散射层编号；当前物理约定为 ch2。 |
| `rear_chamber_id` | integer | 后方吸收层编号；当前物理约定为 ch1。 |
| `minimum_layer_energy_MeV` | number | 判定某层发生有效沉积的最小能量。 |
| `raw_branches` | object | 原始 `eventID`、`chamberID`、位置和沉积能量 Branch 名。 |
| `output_branches` | object | 精简事件的 `r1`、`r2`、`e1` Branch 名。 |

Translator 仍只负责 ETL，不包含重建或敏感度计算。

### 3.4 敏感度矩阵

`SensitivityMatrix` 内部使用连续的一维 `std::vector`：

```text
sensitivity[direction_index * energy_count + energy_index]
```

因此单个 cell 的读取复杂度为 `O(1)`，同时保持良好的缓存局部性。类本身负责：

- 保存方向数和能量数；
- 检查下标范围；
- 检查矩阵尺寸；
- 提供只读 `at(direction, energy)` 查询；
- 禁止把不完整或尺寸不匹配的矩阵静默注入求解器。

LM-MLEM 更新中将显式使用每个 cell 的物理敏感度 `s_j`：

```text
lambda_j^(k+1) = lambda_j^k / s_j
                 * sum_i [ response(i,j) / prediction_i ]
```

实现时必须保留 `s_j > 0` 防护。`s_j <= 0` 的 cell 不参与除法，并被明确置零或跳过，不能产生无穷大或 NaN。

---

## 4. 子系统 2：独立网格兼容器 Grid Resampler

### 4.1 目标架构

```text
v3_json_architecture/GridResampler/
├── config/
│   └── resampler_config.json
├── include/
│   ├── GridAdapter.h
│   ├── ResamplerConfig.h
│   ├── ResamplerIO.h
│   └── 复用主程序的 Grid 与 SensitivityMatrix 接口
└── src/
    ├── GridAdapter.cpp
    ├── ResamplerIO.cpp
    └── resampler_main.cpp
```

该程序既能生成独立可执行文件 `grid_resampler`，也能将 `GridAdapter` 与 `ResamplerIO` 作为普通 C++ 对象链接到其他程序。

### 4.2 `GridResampler/config/resampler_config.json` 参数设计

| 参数 | 类型 | 意义 |
|---|---:|---|
| `input_sensitivity_file` | string | Master 网格上的敏感度 ROOT 文件。 |
| `input_sensitivity_tree` | string | 输入敏感度树名称。 |
| `output_sensitivity_file` | string | Target 网格上的输出敏感度文件。 |
| `output_sensitivity_tree` | string | 输出敏感度树名称。 |
| `master_nside` | integer | 原始 HEALPix 方向网格 Nside。 |
| `target_nside` | integer | 目标重建方向网格 Nside。 |
| `master_energy_grid` | object | Master 能量下界、上界及点数。 |
| `target_energy_grid` | object | Target 能量下界、上界及点数。 |
| `interpolation` | string | `nearest` 或 `polygon`。 |
| `require_full_coverage` | boolean | Target cell 没有任何 Master 覆盖时是否立即报错。 |

### 4.3 两种插值策略

`nearest`：

- 对每个 Target cell 查找球面中心距离最近的 Master 方向像素；
- 能量维度选择最近能量点；
- 速度快，适合调试和同分辨率网格检查；
- 不保证面积守恒。

`polygon`：

- 计算 Target HEALPix 像素与所有候选 Master 像素的球面多边形交叠面积；
- 使用交叠面积作为权重；
- Target 敏感度按下式计算：

```text
s_target = sum(overlap_area_k * s_master_k) / sum(overlap_area_k)
```

- 适合正式的不同 Nside 重采样；
- 实现必须检查面积和、球面边界方向以及数值容差。

---

## 5. 子系统 3：Geant4 双功能模拟器

### 5.1 目标架构

```text
v3_json_architecture/Geant4_Simulation/
├── config/
│   └── sim_config.json
├── include/
│   ├── DetectorConstruction.hh
│   ├── ConfigManager.hh
│   ├── SimulationGrid.hh
│   ├── PrimaryGeneratorAction.hh
│   ├── EventAction.hh
│   ├── RunAction.hh
│   └── 相机几何所需的 Messenger、TrackerHit/SD 和 PhysicsList
├── src/
│   ├── DetectorConstruction.cc
│   ├── SimulationGrid.cpp
│   ├── PrimaryGeneratorAction.cpp
│   ├── EventAction.cpp
│   ├── RunAction.cpp
│   └── main.cpp
└── io/
    ├── root_writer.h
    └── root_writer.cpp
```

`DetectorConstruction` 及其 Messenger 已从指定的 Geant4 相机工程原样复制。V3 只让 `TrackerSD` 停止额外输出 Step ntuple，几何与材料定义未改动。

### 5.2 `Geant4_Simulation/config/sim_config.json` 参数设计

| 参数 | 类型 | 意义 |
|---|---:|---|
| `mode` | integer | `0`：敏感度打表；`1`：直接生成精简重建事件。 |
| `source.hemisphere_radius_mm` | number | 源在相机前半球上的放置半径，单位 mm。 |
| `source.front_hemisphere_only` | boolean | 是否只发射 `z <= 0`（相机正前方）的方向 cell。 |
| `grid.healpix_nside` | integer | 遍历源方向使用的 HEALPix Nside。 |
| `grid.energy_min_MeV` | number | 发射能量网格下界。 |
| `grid.energy_max_MeV` | number | 发射能量网格上界。 |
| `grid.energy_point_count` | integer | 发射能量点数。 |
| `grid.particles_per_cell` | integer | 每个方向－能量 cell 发射的粒子数。 |
| `source.particle_name` | string | Geant4 粒子名，康普顿相机基线通常使用 `gamma`。 |
| `source.emission_cone_half_angle_degree` | number | 指向相机中心的定向发射锥半角。 |
| `random_seed` | integer | 随机种子，用于结果复现。 |
| `trigger.front_chamber_id` | integer | 前层 ch2 的编号。 |
| `trigger.rear_chamber_id` | integer | 后层 ch1 的编号。 |
| `trigger.minimum_layer_energy_MeV` | number | 双层触发所需的最小层沉积能量。 |
| `output.sensitivity_root_file` | string | Mode 0 的敏感度 ROOT 输出。 |
| `output.events_root_file` | string | Mode 1 的精简事件 ROOT 输出。 |

### 5.3 Geant4 Action 职责

- `PrimaryGeneratorAction`：取得当前方向－能量 cell，将源放到半球上，并只在朝向相机中心的小发射锥内取样。
- `EventAction`：缓存本事件的 hit，执行 ch2+ch1 双层触发；Mode 0 只累计计数，Mode 1 直接形成 `r1`、`r2`、`e1`。
- `RunAction`：在 Run 结束时汇总每个 cell 的总发射数和有效数，并计算：

```text
s_emitted = valid_event_count / emitted_particle_count
```

- `root_writer`：只处理 ROOT schema 与写盘，不实现触发物理。
- `main.cpp`：只组装 RunManager、几何、PhysicsList 和 Actions，不放置物理判定逻辑。

---

## 6. 构建目标

根 Makefile 已启用全部 V3 目标。单独构建 Translator 或绘图器：

```bash
make eiid_translator
make eiid_plotter
```

V3 目标：

```bash
make EIID_Recon_V3
make grid_resampler
make libgrid_resampler.a
make geant4_simulator
make v3-all
```

查看目标说明：

```bash
make help
```

依赖：

- 支持 C++17 的 `g++`；
- CERN ROOT，并保证 `root-config` 可用；
- HEALPix C++；
- `nlohmann/json.hpp`；
- 子系统 3 还需要 Geant4，并保证 `geant4-config` 可用。

---

## 7. 完整运行顺序

以项目根目录为当前工作目录：

```bash
cd /path/to/v3_json_architecture
make v3-all
```

所有 JSON 中的相对路径都相对于该 JSON 文件自身所在目录，不受启动程序时的 shell 目录影响。

### 路线 A：直接由新 Geant4 模拟器生成精简事件

```text
1. 配置 sim_config.json，Mode = 0
2. 运行 geant4_simulator，生成 Master 敏感度文件
3. 若模拟网格与重建网格不同，运行 grid_resampler
4. 配置 sim_config.json，Mode = 1
5. 运行 geant4_simulator，生成精简 events.root
6. 配置 recon_config.json
7. 运行 EIID_Recon_V3，生成 result.root
8. 运行 eiid_plotter，生成 figures/*.png
```

对应命令：

```bash
# 先把 sim_config.json 的 mode 设为 0。
./geant4_simulator Geant4_Simulation/config/sim_config.json
./grid_resampler GridResampler/config/resampler_config.json

# 再把 sim_config.json 的 mode 设为 1。
./geant4_simulator Geant4_Simulation/config/sim_config.json
./EIID_Recon_V3 config/recon_config.json
./eiid_plotter vis/plot_config.json
```

### 路线 B：保留 step 级 Geant4 输出

```text
1. Geant4 生成原始 step ROOT 文件
2. eiid_translator 根据 translator_config.json 生成精简 events.root
3. 准备或重采样敏感度文件
4. EIID_Recon_V3 生成 result.root
5. eiid_plotter 生成图片
```

对应命令：

```bash
make eiid_translator EIID_Recon_V3 eiid_plotter
./eiid_translator config/translator_config.json
./EIID_Recon_V3 config/recon_config.json
./eiid_plotter vis/plot_config.json
```

任何生产重建开始前，都必须确认以下三项完全一致：

- 重建 `healpix_nside` 与敏感度 Target Nside；
- 重建能量网格与敏感度 Target 能量网格；
- 二者使用相同的 RING 编号和一维 cell 排列。

不一致时必须显式运行 Grid Resampler 或终止程序，禁止静默按错误下标读取敏感度。
