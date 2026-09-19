# EIID V10——中文用户手册

## 1. 最短正确用法

把外部精简事件文件放在 V10 根目录，文件名为 `events.root`。默认流程只读它，不会生成或覆盖它。

```bash
cd ~/labwork/SourceRecon/EIID_CPP/v10_pixel_integrated_response
make configure
make all
make test
make experiment
```

`make configure` 每台机器只需正常执行一次；它生成 `config/local.mk`，锁定 ROOT、HEALPix、Geant4、JSON、C++20 和 rpath。更换依赖版本后重新执行。

`make experiment` 是高成本正式流程。Nside 32、50 个能量点和多次 MLEM 会明显增加耗时；不要把它当 smoke test。

## 2. 输入文件要求

`events.root` 必须含 `Events` Tree 以及 `Double_t` Branch：

```text
r1_x r1_y r1_z r2_x r2_y r2_z e1_MeV
```

只检查输入，不运行重建：

```bash
make validate-events
```

若只有 Step 级 `raw_steps.root`，可以单独运行 Translator。其默认输出是 `translated_events.root`；检查后由使用者明确复制/改名为 V10 根目录的 `events.root`。

## 3. 总体工作流

```text
外部 events.root ---------------------------------------------+
                                                               |
Geant4 Mode 0 -> efficiency Master -> Nside 8/16/32 efficiency +
                                                               v
Livermore 样本 -> 响应标定 -> Gaussian+Lorentzian 核 -> 四组重建
                                                               |
                                          benchmark + 四组 visualization
```

完整流程等价于：

```bash
make validate-events
make prepare-run
make run-simulation
make run-resampler-all
make run-sample-grid
make calibrate
make reconstruct-pixel-study
make benchmark
make visualize-pixel-study
```

`prepare-run` 不删除旧结果；它把已有 `runs/latest` 移到 `runs/archive/<时间戳>`，并保存本次 JSON 快照及外部事件 SHA-256。

## 4. 分模块运行

### 4.1 绝对效率模拟

```bash
make simulation
make run-simulation
```

配置：`Geant4_Simulation/config/sim_config.json`。默认 Mode 0 输出 `runs/latest/efficiency/absolute_efficiency_master.root`。

主要参数：

| 参数 | 含义 |
|---|---|
| `mode` | `0` 生成绝对效率；`1` 直接生成精简事件 |
| `random_seed` | 随机种子 |
| `source.particle_name` | 粒子名，当前为 `gamma` |
| `source.hemisphere_radius_mm` | 以 ch2 中心为球心的点源半球半径 |
| `source.front_hemisphere_only` | `true` 只模拟相机前半球 |
| `source.emission_cone_safety_margin_degree` | 自动包围探测器的定向锥附加安全角 |
| `environment.world_material` | Geant4 World 材料 |
| `environment.world_margin_mm` | World 超出源和探测器的余量 |
| `grid.healpix_nside` | Master 方向网格，V10 默认 32 |
| `grid.energy_point_count` | 入射能量点数 |
| `grid.energy_min_MeV/max_MeV` | 能量范围 |
| `grid.particles_per_cell` | 每个方向—能量单元发射数 |
| `trigger.front_chamber_id/rear_chamber_id` | ch2/ch1 编号，固定 0/1 |
| `trigger.minimum_layer_energy_MeV` | 两层最低沉积能量 |
| `output.*` | ROOT 路径与 Tree 名 |

### 4.2 网格兼容器

```bash
make resampler
make run-resampler-all
```

它生成 Nside 8、16、32 三份绝对效率。单独运行某份：

```bash
./GridResampler/grid_resampler GridResampler/config/resampler_nside16.json
```

JSON 参数包括输入/输出 ROOT 与 Tree、`master_grid`、`target_grid`、`interpolation` (`nearest|polygon`)、`polygon_subdivision_factor` 和 `require_full_coverage`。效率是概率场，polygon 输出为球面面积平均，不是求和。

### 4.3 Doppler 响应标定

```bash
make run-sample-grid
make calibrate
```

样本配置位于 `DopplerSampleGenerator/config/livermore_*.json`。可调粒子数、单能值、源距离/方向、发射锥、物理模型、选择阈值和输出路径。

`ResponseCalibration/config/calibration_config.json` 控制输入列表、ROOT/JSON/图片输出、散射角边界、ARM 直方图范围、最小训练/测试统计和测试集比例。V10 重建默认使用 `gaussian_lorentzian_mixture`；标定状态不是 usable 时会停止，不会静默换核。

### 4.4 重建

```bash
make reconstruct-center
make reconstruct-integrated-16
make reconstruct-integrated-32
make reconstruct-iteration-20
```

或一次执行四组：

```bash
make reconstruct-pixel-study
```

配置参数：

| 参数 | 含义 |
|---|---|
| `input_events_file/tree` | 外部事件 ROOT 与 Tree |
| `output_result_file/tree` | 重建输出 |
| `absolute_efficiency_file/tree` | 与父网格相同 Nside 的效率图 |
| `healpix_nside` | MLEM 未知图像的父网格 Nside |
| `healpix_ordering` | 当前固定 `RING` |
| `energy_min_MeV/max_MeV` | 重建能量范围 |
| `energy_point_count` | 能量未知量个数 |
| `iteration_count` | MLEM 迭代次数 |
| `response_kernel.type` | ARM 响应核 |
| `response_kernel.calibration_file` | 标定参数 ROOT |
| `pixel_integration.strategy` | `pixel_center` 或 `healpix_subpixel` |
| `pixel_integration.integration_nside` | 响应积分的子像素 Nside |
| `denominator_floor` | 数值保护阈值 |
| `*_branches` | ROOT Branch 映射 |

默认 `recon_config.json` 为父 Nside 32、积分 Nside 64、4 个样本/父像素、10 次迭代。仅想运行已编译程序：

```bash
./Reconstruction/EIID_Recon_V10 Reconstruction/config/recon_config.json
```

### 4.5 比较与画图

```bash
make benchmark
make visualize-pixel-study
```

Benchmark 的 `inputs[]` 控制标签、核类型、结果文件和 Tree；其余参数指定标定状态、真值、JSON 与图片目录。

Visualization 配置控制输入/输出、真值文件、六类图开关、质量 JSON 开关，以及能量包含率、Gaussian 诊断窗口、方向局部半径。单画默认高分辨率结果：

```bash
./Visualization/eiid_plotter Visualization/config/plot_config.json
```

## 5. 独立编译

每个模块均可独立编译，例如：

```bash
make -C PixelIntegration
make -C Reconstruction
make -C GridResampler
make -C Geant4_Simulation
make -C Visualization
```

依赖模块会按各自 Makefile 自动构建。`make clean` 清理全部编译产物；`make -C 模块 clean` 只清理该模块。

## 6. 手工依赖覆盖

优先重新配置，而不是逐个修改 Makefile：

```bash
ROOT_CONFIG=/绝对路径/root-config \
GEANT4_CONFIG=/绝对路径/geant4-config \
EIID_DEPS_PREFIX=/含HEALPix的前缀 \
make configure
```

查看最终设置：

```bash
make show-config
```

必须手改时，只改自动生成的 `config/local.mk`，关键变量为 `CXX`、`PROJECT_CXX_STANDARD`、`ROOT_CONFIG`、`HEALPIX_CFLAGS`、`HEALPIX_LIBS`、`JSON_CFLAGS`、`GEANT4_CONFIG` 和 `EIID_RPATH_FLAGS`。不要在十几个子 Makefile 中重复硬编码路径。

## 7. 常见错误

- `dependency configuration is missing`：先运行 `make configure`。
- 找不到 `healpix_base.h`：检查 `HEALPIX_CFLAGS` 是否指向 `include/healpix_cxx`。
- Geant4 运行时加载旧库：重新 `make configure && make clean && make all`，用 `ldd` 确认路径。
- 缺效率文件：先 `make run-simulation` 和 `make run-resampler-all`。
- 缺 `doppler_response.root`：先 `make run-sample-grid && make calibrate`。
- 响应模型 unusable：增加标定统计或检查拟合，不要绕过门禁。
- Nside 报错：父、积分 Nside 及其比值必须符合 HEALPix 的 2 的整数幂层级。
