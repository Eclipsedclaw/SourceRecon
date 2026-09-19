# Geant4_Simulation——用户手册

## 编译与运行

新机器先在 V5 根目录运行一次 `make configure`。如果脚本没有自动找到 Geant4，可明确指定：

```bash
GEANT4_CONFIG=/geant4-config绝对路径 make configure
```

自动探测会比较 PATH、HOME、`/opt` 和 `/usr/local` 中的全部候选项，忽略 `*-build` 目录，并选择版本号最高的正式 Geant4 安装。即使旧版 `geant4-config` 输出 `-std=c++11`，本模块也始终采用项目统一的 C++20。

```bash
cd Geant4_Simulation
make
make run
```

生成 `config/local.mk` 后，不需要再激活 Conda 环境。
`make run` 会自动初始化配置阶段选中的 Geant4 动态库和数据集。使用其他配置时运行：

```bash
make run SIM_CONFIG=config/其他配置.json
```

## 可调参数

| 分组 | 参数 | 含义 |
|---|---|---|
| 顶层 | `mode` | `0`：生成绝对效率；`1`：生成精简事件 |
| 顶层 | `random_seed` | 正整数 CLHEP 随机种子 |
| source | `particle_name` | Geant4 粒子名，通常为 `gamma` |
| source | `hemisphere_radius_mm` | 点源到 ch2 几何中心的距离，单位 mm |
| source | `front_hemisphere_only` | 是否只模拟 `z <= 0` 的相机前半球 |
| source | `emission_cone_safety_margin_degree` | 自动计算发射锥后额外增加的安全角度 |
| environment | `world_material` | `G4_Galactic` 或 `G4_AIR` |
| environment | `world_margin_mm` | World 超出源球和探测器边界的额外距离 |
| grid | `healpix_nside` | HEALPix Nside，必须是 2 的正整数次幂 |
| grid | `energy_point_count` | 入射能量点数 |
| grid | `energy_min_MeV` | 最低模拟入射能量 |
| grid | `energy_max_MeV` | 最高模拟入射能量 |
| grid | `particles_per_cell` | 每个有效方向—能量单元发射的光子数 |
| trigger | `front_chamber_id` | 必须为 `0`，即 ch2 |
| trigger | `rear_chamber_id` | 必须为 `1`，即 ch1 |
| trigger | `minimum_layer_energy_MeV` | ch2、ch1 各自需要达到的最低沉积能量 |
| output | `absolute_efficiency_root_file` | Mode 0 输出 ROOT 路径 |
| output | `absolute_efficiency_tree_name` | Mode 0 输出 Tree 名 |
| output | `events_root_file` | Mode 1 输出 ROOT 路径 |
| output | `events_tree_name` | Mode 1 输出 Tree 名 |

## Mode 0：绝对效率标定

把 `mode` 设为 `0`，程序会生成 `absolute_efficiency_master.root`。实际参与模拟但零触发的 cell 使用 `(k+0.5)/(N+1)` 平滑；未参与模拟的 cell 仍为严格零。模板中的 `particles_per_cell = 100` 只适合冒烟测试；正式标定必须显著提高统计量，并分别增加粒子数和发射锥安全余量检查结果是否收敛。粒子数增大时，平滑结果自动趋近普通的 `k/N`。

## Mode 1：直接生成精简事件

把 `mode` 设为 `1`，程序会直接生成精简触发事件。输出包含 `eventID`、`source_cell_index`、`r1`、`r2` 与 `e1_MeV`。

若修改源半径、World 材料、探测器几何、触发阈值或能量网格，旧效率标定立即失效，必须重新运行 Mode 0。
