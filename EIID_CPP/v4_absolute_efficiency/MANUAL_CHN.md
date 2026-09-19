# EIID V4 中文用户手册

## 1. 程序用途

V4 提供五个面向用户的可执行程序：

| 程序 | 用途 |
|---|---|
| `Geant4_Simulation/geant4_simulator` | 生成绝对效率图或精简触发事件 |
| `GridResampler/grid_resampler` | 把 Master 效率网格转换为重建网格 |
| `Translator/eiid_translator` | 把原始 Geant4 Step 数据转换为精简事件 |
| `Reconstruction/EIID_Recon_V4` | 执行 EIID + LM-MLEM 重建 |
| `Visualization/eiid_plotter` | 生成全天球图、能谱和累计包含率图 |

常见数据流：

```text
Mode 0 模拟 → Master 绝对效率 → 网格转换 → 重建用绝对效率
Mode 1 模拟或 Translator → 精简事件
绝对效率 + 精简事件 → 重建 → result.root → 可视化
```

## 2. 环境要求

- 支持 C++20 的 `g++`
- GNU Make
- CERN ROOT，并能调用 `root-config`
- HEALPix C++：`healpix_cxx` 与 `cxxsupport`
- `nlohmann/json.hpp`
- 编译模拟器时还需要 Geant4，并能调用 `geant4-config`

项目不再要求每次激活 Conda 环境。在 V4 根目录对每台机器执行一次：

```bash
make configure
```

该命令会生成包含绝对依赖路径的 `config/local.mk`。配置后可用以下命令检查：

```bash
root-config --version
pkg-config --libs healpix_cxx
geant4-config --version
cat config/local.mk
```

Geant4 自动探测会比较 `PATH`、常见环境、HOME、`/opt` 和 `/usr/local` 中的所有候选项，排除 `*-build` 目录，并选择版本号最高的正式安装版本。运行 `make show-config` 可以直接查看最终采用的编译器和 Geant4。

## 3. 编译方法

在 V4 根目录统一编译：

```bash
make configure      # 每台机器只需执行一次
make v4-all
```

以后新开的终端直接运行 `make v4-all`，无需再激活环境。若把项目迁移到另一台服务器，再执行一次 `make configure` 覆盖旧的 `config/local.mk`。

只编译指定模块：

```bash
make common
make reconstruction
make resampler
make simulation
make translator
make visualization
```

也可以进入模块目录独立编译：

```bash
cd Reconstruction
make
```

运行不依赖 ROOT/Geant4 的基础测试：

```bash
make test
```

清理所有编译产物：

```bash
make clean
```

## 4. Geant4 模拟配置

配置文件：`Geant4_Simulation/config/sim_config.json`。

### 顶层参数

| 参数 | 含义 |
|---|---|
| `mode` | `0`：绝对效率标定；`1`：直接生成精简触发事件 |
| `random_seed` | 正整数 CLHEP 随机种子 |

### `source`

| 参数 | 含义 |
|---|---|
| `particle_name` | Geant4 粒子名，通常为 `gamma` |
| `hemisphere_radius_mm` | 点源与 ch2 几何中心的距离，单位 mm |
| `front_hemisphere_only` | `true`：只模拟 `z <= 0` 的前半球；`false`：模拟全天球 |
| `emission_cone_safety_margin_degree` | 在几何自动计算的锥半角上增加的安全余量；它本身不是完整锥半角 |

每个单元的源位置为：

```text
source_position[j] = ch2_center + hemisphere_radius_mm * direction[j]
```

增大源半径会让入射射线更接近平行束，但绝对效率大致按 `1/R²` 降低。

### `environment`

| 参数 | 含义 |
|---|---|
| `world_material` | `G4_Galactic` 表示真空，`G4_AIR` 表示空气 |
| `world_margin_mm` | World 在源球和探测器边界外额外保留的距离 |

World 尺寸会自动计算。修改源半径时不要手工修改几何源码中的 World 尺寸。

### `grid`

| 参数 | 含义 |
|---|---|
| `healpix_nside` | HEALPix 分辨率，必须是 2 的正整数次幂 |
| `energy_point_count` | 模拟的入射能量点数 |
| `energy_min_MeV` | 入射能量下限 |
| `energy_max_MeV` | 入射能量上限 |
| `particles_per_cell` | 每个有效方向—能量单元发射的光子数 |

全天球方向数为 `12 × Nside²`。运行时间与有效方向数、能量点数和每单元粒子数近似成正比。

### `trigger`

| 参数 | 含义 |
|---|---|
| `front_chamber_id` | 本几何必须为 `0`，对应 ch2 |
| `rear_chamber_id` | 本几何必须为 `1`，对应 ch1 |
| `minimum_layer_energy_MeV` | ch2、ch1 各自必须达到的最低沉积能量 |

### `output`

| 参数 | 含义 |
|---|---|
| `absolute_efficiency_root_file` | Mode 0 输出文件路径 |
| `absolute_efficiency_tree_name` | Mode 0 输出 Tree 名 |
| `events_root_file` | Mode 1 输出文件路径 |
| `events_tree_name` | Mode 1 输出 Tree 名 |

相对路径均以 `sim_config.json` 所在目录为基准。

单独运行：

```bash
cd Geant4_Simulation
make run
```

`make run` 会先执行 `config/local.mk` 中选定版本的
`geant4-config --sh`，再启动模拟器。因此即使新开终端，也会自动使用配套的
Geant4 动态库和数据集。若要换配置文件，可运行
`make run SIM_CONFIG=config/quick_test.json`。

## 5. 网格兼容器配置

配置文件：`GridResampler/config/resampler_config.json`。

| 参数 | 含义 |
|---|---|
| `input_absolute_efficiency_file` | Master 效率 ROOT 文件 |
| `input_absolute_efficiency_tree` | Master Tree 名 |
| `output_absolute_efficiency_file` | 转换后效率 ROOT 文件 |
| `output_absolute_efficiency_tree` | 输出 Tree 名 |
| `master_grid.healpix_nside` | Mode 0 模拟所用 Nside |
| `master_grid.energy_min_MeV` | Master 能量下限 |
| `master_grid.energy_max_MeV` | Master 能量上限 |
| `master_grid.energy_point_count` | Master 能量点数 |
| `target_grid.healpix_nside` | 目标重建 Nside |
| `target_grid.energy_min_MeV` | Target 能量下限 |
| `target_grid.energy_max_MeV` | Target 能量上限 |
| `target_grid.energy_point_count` | Target 能量点数 |
| `interpolation` | `nearest` 或 `polygon` |
| `polygon_subdivision_factor` | polygon 公共细分倍率；越大越精确，也越耗时 |
| `require_full_coverage` | Target 像素无覆盖时是否直接报错 |

Target 能量范围必须位于 Master 范围内，源半径元数据会自动保留。

```bash
cd GridResampler
./grid_resampler config/resampler_config.json
```

## 6. 重建配置

配置文件：`Reconstruction/config/recon_config.json`。

### 文件和网格

| 参数 | 含义 |
|---|---|
| `input_events_file` | 精简事件 ROOT 文件 |
| `input_events_tree` | 精简事件 Tree 名 |
| `output_result_file` | 重建结果 ROOT 文件 |
| `output_result_tree` | 重建结果 Tree 名 |
| `absolute_efficiency_file` | 重建使用的绝对效率文件 |
| `absolute_efficiency_tree` | 绝对效率 Tree 名 |
| `healpix_nside` | 重建方向网格 Nside |
| `healpix_ordering` | 必须为 `RING` |
| `energy_min_MeV` | 重建入射能量下限 |
| `energy_max_MeV` | 重建入射能量上限 |
| `energy_point_count` | 重建能量点数 |

重建网格必须与转换后效率文件中的元数据完全一致。

### 算法参数

| 参数 | 含义 |
|---|---|
| `iteration_count` | LM-MLEM 迭代次数 |
| `response_sigma_degree` | 角度高斯响应宽度 |
| `denominator_floor` | 向量长度和预测值的数值零保护阈值 |

### Branch 名称

| 参数 | 含义 |
|---|---|
| `event_branches.r1_x` | ch2 位置 x Branch |
| `event_branches.r1_y` | ch2 位置 y Branch |
| `event_branches.r1_z` | ch2 位置 z Branch |
| `event_branches.r2_x` | ch1 位置 x Branch |
| `event_branches.r2_y` | ch1 位置 y Branch |
| `event_branches.r2_z` | ch1 位置 z Branch |
| `event_branches.e1_MeV` | ch2 沉积能量 Branch |
| `result_branches.cell_index` | 展平单元索引 |
| `result_branches.weight` | 重建强度 |
| `result_branches.healpix_pixel_id` | HEALPix 像素编号 |
| `result_branches.theta_degree` | 极角 |
| `result_branches.phi_degree` | 方位角 |
| `result_branches.direction_x` | 方向 x 分量 |
| `result_branches.direction_y` | 方向 y 分量 |
| `result_branches.direction_z` | 方向 z 分量 |
| `result_branches.energy_MeV` | 当前单元能量 |
| `absolute_efficiency_branches.cell_index` | 效率单元索引 Branch |
| `absolute_efficiency_branches.efficiency` | 绝对效率 Branch，默认名为 `sensitivity` |

```bash
cd Reconstruction
./EIID_Recon_V4 config/recon_config.json
```

## 7. Translator 配置

配置文件：`Translator/config/translator_config.json`。

| 参数 | 含义 |
|---|---|
| `raw_input_file` | Step 级 Geant4 ROOT 输入 |
| `raw_input_tree` | Step 级 Tree 名 |
| `output_events_file` | 精简事件 ROOT 输出 |
| `output_events_tree` | 精简事件 Tree 名 |
| `front_chamber_id` | ch2 编号，通常为 `0` |
| `rear_chamber_id` | ch1 编号，通常为 `1` |
| `minimum_layer_energy_MeV` | 每层触发阈值 |
| `raw_branches.event_id` | 事件分组键 |
| `raw_branches.chamber_id` | 探测层编号 |
| `raw_branches.x` | Step x 坐标 |
| `raw_branches.y` | Step y 坐标 |
| `raw_branches.z` | Step z 坐标 |
| `raw_branches.energy_deposit_MeV` | Step 沉积能量 |
| `output_branches.r1_x` | ch2 质心 x 输出 Branch |
| `output_branches.r1_y` | ch2 质心 y 输出 Branch |
| `output_branches.r1_z` | ch2 质心 z 输出 Branch |
| `output_branches.r2_x` | ch1 质心 x 输出 Branch |
| `output_branches.r2_y` | ch1 质心 y 输出 Branch |
| `output_branches.r2_z` | ch1 质心 z 输出 Branch |
| `output_branches.e1_MeV` | ch2 总沉积能量输出 Branch |

原始输入与精简输出路径不能相同，输入行必须按 `eventID` 非递减排列。

```bash
cd Translator
./eiid_translator config/translator_config.json
```

## 8. 可视化配置

配置文件：`Visualization/config/plot_config.json` 和 `truth_info.json`。

### `plot_config.json`

| 参数 | 含义 |
|---|---|
| `input_root_file` | 重建结果 ROOT 文件 |
| `input_tree_name` | 结果 Tree 名 |
| `output_directory` | PNG 输出目录 |
| `truth_info_file` | 真值 JSON 路径 |
| `draw_skymap` | 是否生成全天球图 |
| `draw_spectrum` | 是否生成能谱 |
| `draw_containment` | 是否生成累计包含率图 |
| `show_truth_markers` | 是否叠加真值方向和能量参考 |

### `truth_info.json`

| 参数 | 含义 |
|---|---|
| `theta_degree` | 真实源极角 |
| `phi_degree` | 真实源方位角 |
| `energy_MeV` | 真实源能量 |

```bash
cd Visualization
./eiid_plotter config/plot_config.json
```

默认图片目录为 `Visualization/figures/`。程序使用 ROOT batch 模式，不需要 X11。

## 9. 常见工作流

### 9.1 制作可复用的 Master 绝对效率图

1. 把 Geant4 `mode` 设为 `0`。
2. 选择 Master Nside、能量网格和足够大的 `particles_per_cell`。
3. 运行 `geant4_simulator`。
4. 确认生成 `absolute_efficiency_master.root`。

### 9.2 转换为计算量较小的重建网格

1. 将 Mode 0 的精确网格参数填入 `master_grid`。
2. 在 `target_grid` 中设置重建需要的网格。
3. 正式计算建议选择 `polygon`。
4. 运行 `grid_resampler`，生成 `absolute_efficiency.root`。

### 9.3 直接生成精简模拟事件

1. 把 Geant4 `mode` 设为 `1`。
2. 设置源和网格参数。
3. 运行 `geant4_simulator`，生成 `events.root`。

Mode 1 是面向触发事件的锥内定向采样。(4\pi) 归一化只用于 Mode 0 的绝对效率，不会作为 Mode 1 的事件权重。

### 9.4 翻译已有原始 Geant4 文件

1. 修改 `Translator/config/translator_config.json`。
2. 运行 `eiid_translator`。
3. 让 Reconstruction 读取生成的 `events.root`。

### 9.5 完整重建和绘图

```bash
./Reconstruction/EIID_Recon_V4 Reconstruction/config/recon_config.json
./Visualization/eiid_plotter Visualization/config/plot_config.json
```

### 9.6 从头完成标定、事件、重建和绘图

```text
Geant4 Mode 0
    ↓
GridResampler
    ↓
Geant4 Mode 1 或 Translator
    ↓
Reconstruction
    ↓
Visualization
```

## 10. 手动调整 Makefile

优先重新运行配置脚本，不要分别修改六个模块的 Makefile：

```bash
EIID_DEPS_PREFIX=/依赖环境绝对路径 \
ROOT_CONFIG=/root-config绝对路径 \
GEANT4_CONFIG=/geant4-config绝对路径 \
make configure
```

生成的 `config/local.mk` 会包含类似内容：

```make
PROJECT_CXX_STANDARD := c++20
CXX := /g++绝对路径
HEALPIX_CFLAGS := -I/绝对路径/include/healpix_cxx
HEALPIX_LIBS := -L/绝对路径/lib -lhealpix_cxx -lcxxsupport
EIID_RPATH_FLAGS := -Wl,-rpath,/绝对路径/lib
```

不要把 `root-config` 或 `geant4-config` 输出的 `-std=` 手工复制进各模块 Makefile。程序会主动过滤这些选项，并在命令末尾只追加 `PROJECT_CXX_STANDARD` 指定的 C++20。

若自动探测找不到 JSON、ROOT 或 Geant4，请把对应前缀或配置程序的绝对路径传给 `make configure`。最后的手动方案是把 `config/local.mk.example` 复制为 `config/local.mk`，并且只修改这一个文件，不要逐个修改模块 Makefile。

单独编译某个模块时，也可以通过 `make EIID_LOCAL_CONFIG=/配置文件绝对路径/local.mk` 使用另一份机器配置。

外部 JSON 头文件目录的写法为：

```make
JSON_CFLAGS := -I/包含nlohmann目录的路径
```

不要向不需要 Geant4 的模块添加 Geant4 库，也不要把所有 `.o` 合并为一个可执行文件；模块独立性是有意保留的设计。

## 11. 重要物理检查

- `hemisphere_radius_mm` 从 ch2 几何中心量起，不是从全局坐标原点量起。
- 改变源半径会改变绝对效率，必须重新标定。
- 增大发射锥安全余量后，修正的绝对效率应在蒙特卡洛误差内保持稳定；若持续上升，说明原来的锥太窄。
- Master 与 Target 的 Nside、排序和能量范围会在运行时校验。
- 很小的 `particles_per_cell` 只能用于检查程序是否能跑通，不能用于正式标定。
- 包含率图的角分辨率不能解释到小于 HEALPix 像素尺度。
