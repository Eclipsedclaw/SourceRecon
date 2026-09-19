# EIID V3 操作说明书

## 1. 这份说明书管什么

本文档说明 `v3_json_architecture` 的编译方法、全部 JSON 参数、各程序的单独运行方法，以及常用的组合工作流。

以下命令默认已经进入项目根目录：

```bash
cd <v3_json_architecture 所在路径>
```

### 最重要的三条规则

1. 所有 JSON 中的相对路径，都相对于该 JSON 文件所在的目录，不是相对于终端当前目录。
2. ROOT 输出使用 `RECREATE`。如果目标文件已经存在，会被覆盖。
3. 重建网格和敏感度网格的 Nside、能量下界、能量上界、能量点数和 `RING` 顺序必须完全一致。

---

## 2. 程序、配置和输入输出对照表

| 程序 | 用途 | 默认配置 | 主要输入 | 默认输出 |
|---|---|---|---|---|
| `geant4_simulator` | Geant4 敏感度打表或精简事件生成 | `Geant4_Simulation/config/sim_config.json` | 模拟参数 | Mode 0: `sensitivity_master.root`; Mode 1: `events.root` |
| `grid_resampler` | 敏感度网格兼容和重采样 | `GridResampler/config/resampler_config.json` | `sensitivity_master.root` | `sensitivity.root` |
| `eiid_translator` | 将 Step 级 Geant4 ROOT 转换为精简事件 | `config/translator_config.json` | 原始 `Tree1` | `events.root` |
| `EIID_Recon_V3` | 执行 EIID/LM-MLEM 重建 | `config/recon_config.json` | `events.root` + `sensitivity.root` | `result.root` |
| `eiid_plotter` | 由 `result.root` 生成图片 | `vis/plot_config.json` | `result.root` + `truth_info.json` | `figures/*.png` |

默认文件流：

```text
Geant4 Mode 0
    -> sensitivity_master.root
    -> grid_resampler
    -> sensitivity.root

Geant4 Mode 1 或 eiid_translator
    -> events.root

events.root + sensitivity.root
    -> EIID_Recon_V3
    -> result.root
    -> eiid_plotter
    -> figures/*.png
```

---

## 3. 编译环境与 Make 目标

### 3.1 所需依赖

- 支持 C++17 的 `g++`。
- CERN ROOT，且 `root-config` 可用。
- HEALPix C++ 库。
- `nlohmann/json.hpp`。
- 只有 `geant4_simulator` 需要 Geant4，且 `geant4-config` 可用。
- `ar`，用于生成 `libgrid_resampler.a`。

编译前可以先检查：

```bash
command -v g++
command -v root-config
command -v pkg-config
command -v geant4-config

root-config --version
root-config --cflags
root-config --glibs
pkg-config --cflags --libs healpix_cxx
```

如果 Geant4 是单独安装的，先加载它的环境脚本：

```bash
source <Geant4 安装目录>/bin/geant4.sh
```

### 3.2 编译全部程序

```bash
make v3-all
```

`make` 不带目标时也等价于 `make v3-all`。

### 3.3 只编译某个程序

```bash
make geant4_simulator
make grid_resampler
make EIID_Recon_V3
make eiid_translator
make eiid_plotter
```

如果只需要网格兼容器的静态库：

```bash
make libgrid_resampler.a
```

### 3.4 清理编译产物

```bash
make clean
```

这只删除 `.o`、静态库和可执行文件，不删除 JSON、ROOT 数据和 PNG 图片。

### 3.5 查看 Make 将执行什么

```bash
make -n EIID_Recon_V3
make -n grid_resampler
make -n geant4_simulator
make help
```

`-n` 只打印命令，不真正编译，适合检查头文件路径和链接库。

---

## 4. Geant4 模拟配置说明

配置文件：`Geant4_Simulation/config/sim_config.json`

### 4.1 顶层参数

| 参数 | 含义 | 调节影响 |
|---|---|---|
| `mode` | `0` 表示敏感度打表；`1` 表示直接生成精简事件 | Mode 0 写 `sensitivity_root_file`；Mode 1 写 `events_root_file` |
| `random_seed` | Geant4/CLHEP 随机数种子，必须为正整数 | 种子相同且其他条件一致时，用于复现模拟 |

### 4.2 `source` 参数

| 参数 | 含义 | 注意事项 |
|---|---|---|
| `particle_name` | Geant4 粒子名 | 当前康普顿模拟应使用 `gamma`。改为其他粒子前，必须确认 `MyPhysicsList` 已构造它并注册了需要的过程 |
| `hemisphere_radius_mm` | 源点相对相机原点的半球半径，单位 mm | 源必须位于 Geant4 World 内。当前 `40.0 mm` 是针对现有几何的安全默认值 |
| `front_hemisphere_only` | `true` 时只模拟 `z <= 0` 的相机前半球；`false` 时模拟全球 | 设为 `false` 大约会将方向 cell 数加倍，也会模拟相机后方 |
| `emission_cone_half_angle_degree` | 以“源指向相机中心”为轴的定向发射锥半角 | 越小越节省无效追迹，但敏感度表代表的是该发射锥内的有效触发概率 |

### 4.3 `grid` 参数

| 参数 | 含义 | 调节影响 |
|---|---|---|
| `healpix_nside` | 模拟源方向的 HEALPix Nside | 全球方向数是 `12 * Nside^2`。当前程序要求正的 2 的整数次幂 |
| `energy_point_count` | 入射能量网格的点数 | 与方向数相乘得到联合 cell 数 |
| `energy_min_MeV` | 入射能量下界 | 单位 MeV |
| `energy_max_MeV` | 入射能量上界 | 单位 MeV，不能小于下界 |
| `particles_per_cell` | 每个活跃的方向—能量 cell 发射的粒子数 | 越大统计涨落越小，但运行时间线性增长 |

总模拟事件数为：

```text
active_direction_count * energy_point_count * particles_per_cell
```

### 4.4 `trigger` 参数

| 参数 | 含义 | 默认物理约定 |
|---|---|---|
| `front_chamber_id` | 前层的 chamber ID | `0`，即 ch2；对应输出的 `r1` 和 `e1` |
| `rear_chamber_id` | 后层的 chamber ID | `1`，即 ch1；对应输出的 `r2` |
| `minimum_layer_energy_MeV` | 每层通过触发判定的最小总沉积能量 | 前后两层都必须严格大于该值 |

### 4.5 `output` 参数

| 参数 | 含义 |
|---|---|
| `sensitivity_root_file` | Mode 0 生成的敏感度 ROOT 路径 |
| `sensitivity_tree_name` | 敏感度 TTree 名称，默认 `Sensitivity` |
| `events_root_file` | Mode 1 生成的精简事件 ROOT 路径 |
| `events_tree_name` | 精简事件 TTree 名称，默认 `Events` |

### 4.6 单独运行模拟程序

编译：

```bash
make geant4_simulator
```

使用默认配置：

```bash
./geant4_simulator
```

指定另一份配置：

```bash
./geant4_simulator path/to/my_sim_config.json
```

建议为两种模式分别保留配置，避免来回修改 `mode`：

```bash
cp Geant4_Simulation/config/sim_config.json Geant4_Simulation/config/sim_sensitivity.json
cp Geant4_Simulation/config/sim_config.json Geant4_Simulation/config/sim_events.json
```

- 在 `sim_sensitivity.json` 中设置 `"mode": 0`。
- 在 `sim_events.json` 中设置 `"mode": 1`。
- 两份配置应使用不同的输出文件。

```bash
./geant4_simulator Geant4_Simulation/config/sim_sensitivity.json
./geant4_simulator Geant4_Simulation/config/sim_events.json
```

### 4.7 模拟一致性要求

- Mode 0 和将来要处理的 Mode 1 事件应使用同一探测器几何、物理列表、发射锥和触发阈值。
- 改动 `emission_cone_half_angle_degree`、chamber ID、触发阈值或探测器几何后，应重新生成敏感度。
- Mode 0 中对于每个 cell，输出敏感度为：

```text
s_emitted = valid_count / emitted_count
```

---

## 5. Grid Resampler 配置说明

配置文件：`GridResampler/config/resampler_config.json`

### 5.1 输入输出参数

| 参数 | 含义 |
|---|---|
| `input_sensitivity_file` | Master 网格的敏感度 ROOT 文件 |
| `input_sensitivity_tree` | Master 敏感度 TTree 名称 |
| `output_sensitivity_file` | Target 网格的输出 ROOT 文件 |
| `output_sensitivity_tree` | Target 敏感度 TTree 名称 |

### 5.2 `master_grid` 和 `target_grid`

两个对象都包含以下参数：

| 参数 | 含义 |
|---|---|
| `healpix_nside` | Master 或 Target 方向网格的 Nside |
| `energy_min_MeV` | 能量网格下界 |
| `energy_max_MeV` | 能量网格上界 |
| `energy_point_count` | 能量点数 |

`master_grid` 必须与输入 ROOT 的物理网格完全一致。

`target_grid` 必须与后续 `recon_config.json` 的网格完全一致。

当前实现要求 Target 能量范围位于 Master 能量范围内，不做范围外外推。

### 5.3 插值参数

| 参数 | 含义 | 适用情况 |
|---|---|---|
| `interpolation` | `nearest` 或 `polygon` | 决定方向维的重采样方法 |
| `polygon_subdivision_factor` | `polygon` 模式的共同细分倍数 | 越大面积交叠估计越细，但运行时间和内存上升。必须为正整数 |
| `require_full_coverage` | Target 像素无 Master 覆盖时是否报错 | 正式计算建议保持 `true` |

`nearest` 模式：

- 方向使用 Target 像素中心所在的 Master 像素。
- 能量使用距离最近的 Master 能量点。
- 适合快速调试和同网格复制。

`polygon` 模式：

- 通过共同的 HEALPix 等面积微像素统计 Master/Target 球面像素交叠面积。
- 方向按交叠面积加权。
- 能量维使用线性插值。
- 适合正式的不同 Nside 敏感度转换。

### 5.4 单独运行网格兼容器

```bash
make grid_resampler
./grid_resampler
```

指定配置：

```bash
./grid_resampler path/to/my_resampler_config.json
```

运行前确认：

1. `input_sensitivity_file` 存在。
2. 树名和 Branch 是标准敏感度 schema。
3. ROOT 中的 `healpix_nside`、`healpix_ordering`、`direction_count`、`energy_count` 元数据与 `master_grid` 一致。
4. 输出路径不要和输入路径相同，否则会覆盖 Master 文件。

---

## 6. Translator 配置说明

配置文件：`config/translator_config.json`

### 6.1 文件和触发参数

| 参数 | 含义 |
|---|---|
| `raw_input_file` | 原始 Geant4 Step 级 ROOT 文件 |
| `raw_input_tree` | 原始 Step 树名，默认 `Tree1` |
| `output_events_file` | 转换后的精简事件 ROOT 文件 |
| `output_events_tree` | 精简事件树名，默认 `Events` |
| `front_chamber_id` | 前层 ch2 ID，默认 `0`，输出为 `r1/e1` |
| `rear_chamber_id` | 后层 ch1 ID，默认 `1`，输出为 `r2` |
| `minimum_layer_energy_MeV` | 前后两层各自需要超过的最小总沉积能量 |

Translator 将相同 `eventID` 的连续 Step 收集到一个 Buffer，对每个 chamber 计算能量加权质心。原始树必须按 `eventID` 非递减排列。

### 6.2 `raw_branches`

这些键的名字是固定的，它们的值要改成原始 ROOT 里的真实 Branch 名。

| 参数 | 物理内容 | 默认 Branch |
|---|---|---|
| `event_id` | Geant4 事件编号 | `eventID` |
| `chamber_id` | Step 所在探测层编号 | `chamberID` |
| `x` | Step 位置 x | `x_post` |
| `y` | Step 位置 y | `y_post` |
| `z` | Step 位置 z | `z_post` |
| `energy_deposit_MeV` | Step 沉积能量，单位 MeV | `eDep_MeV` |

### 6.3 `output_branches`

| 参数 | 含义 | 标准名称 |
|---|---|---|
| `r1_x`, `r1_y`, `r1_z` | 前层 ch2 的能量加权质心 | 同名 |
| `r2_x`, `r2_y`, `r2_z` | 后层 ch1 的能量加权质心 | 同名 |
| `e1_MeV` | 前层 ch2 的总沉积能量 | `e1_MeV` |

如果修改这些输出 Branch 名，必须同时修改 `recon_config.json` 的 `event_branches`。

### 6.4 单独运行 Translator

```bash
make eiid_translator
./eiid_translator
```

指定配置：

```bash
./eiid_translator path/to/my_translator_config.json
```

Translator 在打开输出文件前会拒绝“原始输入路径与输出路径相同”的配置。

---

## 7. 重建配置说明

配置文件：`config/recon_config.json`

### 7.1 输入输出参数

| 参数 | 含义 |
|---|---|
| `input_events_file` | Translator 或 Geant4 Mode 1 生成的精简事件 ROOT |
| `input_events_tree` | 精简事件 TTree 名称 |
| `output_result_file` | 重建联合图的 ROOT 输出 |
| `output_result_tree` | 重建结果 TTree 名称 |
| `sensitivity_file` | 与重建网格一致的敏感度 ROOT |
| `sensitivity_tree` | 敏感度 TTree 名称 |

### 7.2 网格参数

| 参数 | 含义 |
|---|---|
| `healpix_nside` | 重建方向网格 Nside，方向数为 `12 * Nside^2` |
| `healpix_ordering` | HEALPix 编号顺序。当前必须是 `RING` |
| `energy_min_MeV` | 候选入射能量下界 |
| `energy_max_MeV` | 候选入射能量上界 |
| `energy_point_count` | 候选能量点数 |

敏感度读取器会检查 ROOT 元数据和每行能量坐标。不一致时直接终止，不会静默使用错误下标。

### 7.3 算法参数

| 参数 | 含义 | 调节影响 |
|---|---|---|
| `iteration_count` | LM-MLEM 迭代次数 | 过少可能没收敛；过多可能放大统计噪声，也会线性增加时间 |
| `response_sigma_degree` | 几何散射角与能量散射角之差的高斯响应宽度，单位度 | 越小响应越尖锐，对误差也越敏感 |
| `denominator_floor` | 分母数值安全下限 | 防止近零分母。过大可能错判本来可解释的事件 |
| `require_complete_sensitivity` | 是否要求每个联合 cell 都在敏感度文件中出现 | 正式重建建议保持 `true`；`false` 时缺失 cell 保持零敏感度 |

LM-MLEM 更新中，只有 `s_j > 0` 的 cell 才会执行敏感度除法。`s_j <= 0` 的 cell 始终被置零。

### 7.4 `event_branches`

这些参数说明从输入事件树的哪些 Branch 取出 `r1`、`r2` 和 `e1`。

| JSON 键 | 物理量 |
|---|---|
| `r1_x`, `r1_y`, `r1_z` | 第一个 hit/前层 ch2 位置 |
| `r2_x`, `r2_y`, `r2_z` | 第二个 hit/后层 ch1 位置 |
| `e1_MeV` | 第一层总沉积能量 |

JSON 的键名不要改，只改右侧字符串值来适配不同 ROOT schema。

### 7.5 `result_branches`

| JSON 键 | 输出物理量 |
|---|---|
| `cell_index` | 联合网格一维下标 |
| `weight` | 该方向—能量 cell 的重建强度 |
| `healpix_pixel_id` | HEALPix RING 像素 ID |
| `theta_degree` | 从 `+Z` 轴量起的极角，单位度 |
| `phi_degree` | 绕 Z 轴的方位角，单位度 |
| `direction_x`, `direction_y`, `direction_z` | 源方向单位向量 |
| `energy_MeV` | 该 cell 的候选入射能量 |

`eiid_plotter` 当前按上表的标准 Branch 名读取。如果只在 `recon_config.json` 中改名，绘图程序将找不到 Branch。因此除非同时计划修改绘图代码，建议保持默认值。

### 7.6 `sensitivity_branches`

| JSON 键 | 敏感度树内容 |
|---|---|
| `direction_index` | 方向下标 |
| `energy_index` | 能量下标 |
| `healpix_pixel_id` | HEALPix 像素 ID，当前必须与 `direction_index` 一致 |
| `energy_MeV` | 该行能量坐标 |
| `sensitivity` | 该 cell 的敏感度 `s_j` |

### 7.7 单独运行重建程序

```bash
make EIID_Recon_V3
./EIID_Recon_V3
```

指定配置：

```bash
./EIID_Recon_V3 path/to/my_recon_config.json
```

重建程序本身不会自动运行模拟、Translator 或 Resampler。单独运行前必须已经准备好：

1. 符合 `event_branches` 的精简事件 ROOT。
2. 符合 `sensitivity_branches` 和当前网格的敏感度 ROOT。
3. 事件树至少包含一个有效事件。

---

## 8. 可视化配置说明

### 8.1 `vis/plot_config.json`

| 参数 | 含义 |
|---|---|
| `input_root_file` | 重建结果 ROOT 文件 |
| `input_tree_name` | 重建结果 TTree 名称，必须与 `output_result_tree` 一致 |
| `output_directory` | PNG 输出目录 |
| `truth_info_file` | 真值 JSON 路径，相对于 `plot_config.json` |
| `draw_skymap` | 是否绘制全天球热力图 |
| `draw_spectrum` | 是否绘制方向边缘化后的能谱 |
| `draw_containment` | 是否绘制方向累计包含率及 R50/R68/R90 |
| `show_truth_markers` | 是否在天图和能谱中显示真值标记 |

当前 `VisConfig` 会读取 `truth_info_file`，即使 `show_truth_markers` 是 `false`。因此该文件必须存在且格式正确。`ContainmentPlotter` 本身也必须使用真实源方向。

### 8.2 `vis/truth_info.json`

| 参数 | 含义 |
|---|---|
| `theta_degree` | 真实源方向的极角，从 `+Z` 轴量起，范围 `[0, 180]` |
| `phi_degree` | 真实源方向的方位角，单位度 |
| `energy_MeV` | 真实源能量，单位 MeV，必须为正数 |

相机正前方是 Geant4 的 `-Z` 方向，对应：

```text
theta_degree = 180
```

当源严格位于极点时，`phi_degree` 对物理方向没有影响。

### 8.3 单独运行绘图程序

```bash
make eiid_plotter
./eiid_plotter
```

指定配置：

```bash
./eiid_plotter path/to/my_plot_config.json
```

绘图程序使用 ROOT batch 模式，不需要 X11 弹窗。

---

## 9. 常见工作流

### 9.1 工作流 A：完整新模拟、重采样、重建和绘图

适用于：从 Geant4 开始生成一套完整结果，且敏感度打表网格与重建网格不同。

1. 将 Mode 0 模拟配置的网格设为 Master 网格。
2. 运行 Mode 0，生成 `sensitivity_master.root`。
3. 使 `resampler_config.json` 的 `master_grid` 等于 Mode 0 网格。
4. 使 `target_grid` 等于 `recon_config.json` 网格。
5. 运行 Resampler，生成 `sensitivity.root`。
6. 运行 Mode 1，生成 `events.root`。
7. 运行重建，生成 `result.root`。
8. 更新真值配置并绘图。

```bash
make v3-all

./geant4_simulator Geant4_Simulation/config/sim_sensitivity.json
./grid_resampler GridResampler/config/resampler_config.json
./geant4_simulator Geant4_Simulation/config/sim_events.json
./EIID_Recon_V3 config/recon_config.json
./eiid_plotter vis/plot_config.json
```

### 9.2 工作流 B：模拟网格和重建网格完全一致

适用于：Mode 0 已经直接按重建网格打表。

此时可以跳过 Resampler，但必须让 `recon_config.json` 的 `sensitivity_file` 直接指向 Mode 0 输出：

```bash
./geant4_simulator Geant4_Simulation/config/sim_sensitivity.json
./geant4_simulator Geant4_Simulation/config/sim_events.json
./EIID_Recon_V3 config/recon_config.json
./eiid_plotter vis/plot_config.json
```

跳过 Resampler 的必要条件：

```text
simulation Nside       = reconstruction Nside
simulation energy min  = reconstruction energy min
simulation energy max  = reconstruction energy max
simulation energy count = reconstruction energy count
```

### 9.3 工作流 C：使用既有精简事件和敏感度直接重建

适用于：已经有符合 schema 的 `events.root` 和网格一致的 `sensitivity.root`。

```bash
make EIID_Recon_V3 eiid_plotter
./EIID_Recon_V3 config/recon_config.json
./eiid_plotter vis/plot_config.json
```

不需要运行 Geant4、Translator 或 Resampler。

### 9.4 工作流 D：使用既有 Step 级 Geant4 ROOT

适用于：已经有 `Tree1`，但还没有精简事件树。

```bash
make eiid_translator EIID_Recon_V3 eiid_plotter

./eiid_translator config/translator_config.json
./EIID_Recon_V3 config/recon_config.json
./eiid_plotter vis/plot_config.json
```

此工作流仍然需要事先准备好与重建网格一致的敏感度文件。

### 9.5 工作流 E：只转换敏感度网格

适用于：已有 Master 敏感度，想为另一种重建分辨率生成 Target 敏感度。

```bash
make grid_resampler
./grid_resampler GridResampler/config/resampler_config.json
```

该步骤不需要事件文件，也不会运行重建。

### 9.6 工作流 F：只更换绘图选项或真值

适用于：`result.root` 没有变，只想重新出图。

1. 修改 `vis/plot_config.json` 的开关。
2. 修改 `vis/truth_info.json` 的真值。
3. 单独运行绘图程序。

```bash
./eiid_plotter vis/plot_config.json
```

无需重新模拟或重建。

### 9.7 工作流 G：扫描多组参数

不要反复覆盖同一份配置和 ROOT 文件。建议每组参数使用独立 JSON 和独立输出名，例如：

```text
config/recon_nside8.json       -> results/result_nside8.root
config/recon_nside16.json      -> results/result_nside16.root

GridResampler/config/to_nside8.json
GridResampler/config/to_nside16.json
```

运行时显式传入配置：

```bash
./EIID_Recon_V3 config/recon_nside8.json
./EIID_Recon_V3 config/recon_nside16.json
```

---

## 10. 何时必须重新生成哪些文件

| 改动 | 必须重新做什么 |
|---|---|
| 只改绘图开关、图片目录或真值 | 只重新运行 `eiid_plotter` |
| 只改 `iteration_count` 或 `response_sigma_degree` | 重新运行 `EIID_Recon_V3`，不必重新模拟 |
| 改重建 Nside 或能量网格 | 必须获得对应 Target 敏感度；可重新模拟或运行 Resampler |
| 改 Geant4 几何、材料或 PhysicsList | 必须重新生成敏感度，通常也应重新生成事件 |
| 改触发阈值或 chamber ID | 必须使敏感度与事件生成使用同一判定，并重新生成对应数据 |
| 改发射锥半角 | 必须重新生成敏感度，并保持 Mode 0/1 一致 |
| 只增加 `particles_per_cell` | 重新运行模拟，以降低敏感度的统计误差 |
| 改 Translator 的输出 Branch 名 | 同步修改 `recon_config.json` 的 `event_branches` |

---

## 11. 手动调整 Makefile

### 11.1 优先使用命令行覆盖，不直接改文件

Makefile 中以 `?=` 定义的工具可以在命令行覆盖：

```bash
make EIID_Recon_V3 CXX=/path/to/g++ ROOT_CONFIG=/path/to/root-config

make geant4_simulator \
    CXX=/path/to/g++ \
    ROOT_CONFIG=/path/to/root-config \
    GEANT4_CONFIG=/path/to/geant4-config
```

也可以先设置环境变量：

```bash
export CONDA_PREFIX=/path/to/conda/env
make grid_resampler
```

### 11.2 HEALPix 找不到时

Makefile 先执行：

```bash
pkg-config --cflags --libs healpix_cxx
```

如果找不到 `.pc` 文件，则使用：

```makefile
HEALPIX_CFLAGS = -I$(CONDA_PREFIX)/include/healpix_cxx
HEALPIX_LIBS = -L$(CONDA_PREFIX)/lib -lhealpix_cxx -lcxxsupport
```

如果 HEALPix 不在 Conda 中，将这两行改成实际安装路径：

```makefile
HEALPIX_CFLAGS = -I/actual/healpix/include/healpix_cxx
HEALPIX_LIBS = -L/actual/healpix/lib -lhealpix_cxx -lcxxsupport
```

可以先检查文件是否存在：

```bash
ls /actual/healpix/include/healpix_cxx/healpix_base.h
ls /actual/healpix/lib/libhealpix_cxx.*
ls /actual/healpix/lib/libcxxsupport.*
```

### 11.3 `nlohmann/json.hpp` 找不到时

默认后备路径是：

```makefile
JSON_CFLAGS = -I$(CONDA_PREFIX)/include
```

如果头文件在其他地方，改为包含 `nlohmann/` 目录的上一层：

```makefile
JSON_CFLAGS = -I/actual/json/include
```

应当能看到：

```text
/actual/json/include/nlohmann/json.hpp
```

### 11.4 ROOT 找不到时

首先尽量加载 ROOT 环境，而不是手写所有库：

```bash
source <ROOT 安装目录>/bin/thisroot.sh
root-config --cflags --glibs
```

如果 `root-config` 不在 `PATH`：

```bash
make EIID_Recon_V3 ROOT_CONFIG=/actual/root/bin/root-config
```

只有在确实没有 `root-config` 时，才建议在 Makefile 中直接设置：

```makefile
ROOT_CFLAGS = -I/actual/root/include
ROOT_LIBS = -L/actual/root/lib <实际需要的 ROOT 库>
```

### 11.5 Geant4 找不到时

优先：

```bash
source /actual/geant4/bin/geant4.sh
geant4-config --cflags --libs
make geant4_simulator
```

或者：

```bash
make geant4_simulator GEANT4_CONFIG=/actual/geant4/bin/geant4-config
```

当 `GEANT4_LIBS` 为空时，`geant4_simulator` 目标会明确报错。

### 11.6 切换 Debug 和 Release

当前默认：

```makefile
COMMON_CXXFLAGS := -std=c++17 -O2 -Wall -Wextra -pedantic
```

调试阶段可以改为：

```makefile
COMMON_CXXFLAGS := -std=c++17 -O0 -g3 -Wall -Wextra -pedantic
```

正式计算可以使用：

```makefile
COMMON_CXXFLAGS := -std=c++17 -O3 -DNDEBUG -Wall -Wextra -pedantic
```

改编译选项后必须清理旧对象文件：

```bash
make clean
make v3-all
```

### 11.7 新增 `.cpp` 文件时

- 重建子系统：把文件加入 `V3_RECONSTRUCTION_SOURCES`。
- 绘图子系统：把文件加入 `PLOTTER_SOURCES`。
- Translator：把文件加入 `TRANSLATOR_SOURCES`。
- Grid Resampler 库：把对应 `.o` 加入 `GRID_RESAMPLER_LIBRARY_OBJECTS`。
- Geant4 的 `Geant4_Simulation/src/*.cpp`、`*.cc` 和 `Geant4_Simulation/io/*.cpp` 使用 `wildcard`，放在这些目录下时会自动加入。

如果新文件在新子目录，还要为它增加对应的 `-I...` 和模式规则。

### 11.8 手动改 Makefile 时的语法注意点

- recipe 命令前必须是 Tab，不能用普通空格代替。
- 链接库应放在对象文件后面，例如 `$(CXX) objects -o target $(ROOT_LIBS)`。
- `:=` 是立即展开，`=` 是延迟展开，`?=` 只在变量尚未定义时赋值。
- 调整库路径后先用 `make -n <target>` 检查，再真正编译。
- 如果更换了编译器、头文件路径或宏，先执行 `make clean`。

---

## 12. 常见报错快速排查

### `Cannot open ... ROOT file`

- 检查 JSON 里的路径。
- 记住相对路径以 JSON 所在目录为基准。
- 使用 `ls -l <解析后的实际路径>` 检查。

### `Cannot find ROOT tree`

- 输入文件存在，但 JSON 里的 Tree 名不匹配。
- 使用 ROOT 检查：

```bash
rootls -t file.root
```

### `Missing ... ROOT branch`

- 检查 `event_branches`、`sensitivity_branches` 或 Translator 的 `raw_branches`。
- 不要改 JSON 键名，只改键对应的 Branch 字符串。

### `Sensitivity ROOT metadata does not match`

- 敏感度的 Nside、方向数、能量点数或 RING 顺序与重建配置不同。
- 改正 `recon_config.json`，或者运行 `grid_resampler` 生成正确的 Target 敏感度。

### `An event cannot be explained by any cell with positive sensitivity`

- 事件的能量或散射几何超出当前重建网格的解释范围。
- 检查能量范围、`e1_MeV` 单位、hit 顺序和敏感度正值区域。
- 不要首先通过盲目调大 `denominator_floor` 掩盖该问题。

### `geant4-config was not found`

```bash
source <Geant4 安装目录>/bin/geant4.sh
command -v geant4-config
make clean
make geant4_simulator
```

### `healpix_base.h: No such file or directory`

- 检查 `CONDA_PREFIX`。
- 检查 `HEALPIX_CFLAGS` 指向的目录下是否真的存在 `healpix_base.h`。
- 用 `make -n` 查看最终的 `-I` 参数。

### 链接时出现 `undefined reference`

- 查看缺失符号属于 ROOT、HEALPix、`cxxsupport` 还是 Geant4。
- 检查对应 `*_LIBS` 是否出现在最终链接命令的尾部。
- 检查库和编译器 ABI 是否来自同一套 Conda/系统环境。

---

## 13. 正式运行前检查清单

- [ ] 已备份不能被覆盖的 ROOT 文件。
- [ ] Mode 0 和 Mode 1 的几何、物理列表、触发阈值和发射锥一致。
- [ ] Resampler `master_grid` 与 Master ROOT 一致。
- [ ] Resampler `target_grid` 与重建网格一致。
- [ ] `events.root` 的 Tree 和 Branch 与 `recon_config.json` 一致。
- [ ] `sensitivity.root` 的 Tree、Branch、RING 元数据和能量坐标与重建配置一致。
- [ ] `vis/plot_config.json` 指向本次的 `result.root`。
- [ ] `vis/truth_info.json` 已更新为本次模拟真值。
- [ ] 已使用 `make -n` 检查头文件和链接路径。
- [ ] 改过编译选项或依赖路径后，已执行 `make clean`。
