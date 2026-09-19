# EIID V9 响应模型实验版——中文用户手册

## 1. 最短使用方法

把外部输入放在 V9 根目录：

```text
v9_response_mixture_experiment/events.root
```

然后执行：

```bash
cd ~/labwork/SourceRecon/EIID_CPP/v9_response_mixture_experiment
make configure
make experiment
```

`make configure` 只需要在新机器、依赖位置改变或删除 `config/local.mk` 后重新运行。`make experiment` 会自动编译缺失目标，无需预先 `make clean`。

## 2. 外部 events.root 要求

默认 Tree 为 `Events`，必须包含以下 `Double_t` Branch：

```text
r1_x  r1_y  r1_z
r2_x  r2_y  r2_z
e1_MeV
```

V9 不会生成或覆盖该文件。完整流程开始时先执行等价于 `make validate-events` 的检查；Tree、Branch、类型或数据行非法时，会在耗时模拟之前停止。

## 3. 一键实验流程

```text
校验外部 events.root
→ 归档旧 runs/latest
→ 模拟绝对效率主网格
→ 转换效率网格
→ 生成五个能量的 Doppler 标定样本
→ 拟合 Double Gaussian、Voigt、Gaussian–Lorentzian mixture
→ 排除未完全收敛模型
→ 用同一 events.root 重建所有可用模型
→ Benchmark
→ 为每个可用模型画图
```

如果 Voigt 未收敛，屏幕会显示 `SKIPPED`；这不是程序崩溃。真正的构建、文件或配置错误仍会停止流程。

## 4. 分阶段运行

```bash
make all                    # 只编译全部模块
make test                   # 单元测试
make validate-events        # 只校验外部 events.root
make prepare-run            # 归档旧运行并建立 runs/latest
make run-simulation         # 生成绝对效率主网格
make run-resampler          # 转换为重建效率网格
make run-sample-grid        # 生成五个标定能量
make calibrate              # 拟合三个响应模型
make reconstruct-eligible   # 只重建全部收敛的模型
make benchmark              # 比较可用结果
make visualize-eligible     # 为可用结果画图
```

单独运行某个模型：

```bash
make reconstruct-double-gaussian
make reconstruct-gaussian-lorentzian
make reconstruct-voigt
```

## 5. 主要配置参数

### `Geant4_Simulation/config/sim_config.json`

- `mode`：完整实验应为 `0`，生成绝对效率图。
- `random_seed`：随机种子。
- `source.hemisphere_radius_mm`：以 ch2 中心为球心的源半球半径。
- `source.front_hemisphere_only`：是否只模拟相机前半球。
- `source.emission_cone_safety_margin_degree`：自动包围探测器发射锥的安全余量。
- `grid.healpix_nside`：效率主网格 Nside，必须为 2 的整数幂。
- `grid.energy_point_count`、`energy_min_MeV`、`energy_max_MeV`：能量网格。
- `grid.particles_per_cell`：每个方向—能量 cell 的模拟粒子数。
- `trigger.*`：前后层编号和最小沉积能量。

### `GridResampler/config/resampler_config.json`

- `master_grid`：必须与效率模拟网格一致。
- `target_grid`：必须与重建网格一致。
- `interpolation`：`nearest` 或 `polygon`。
- `polygon_subdivision_factor`：多边形面积法细分程度。
- `require_full_coverage`：是否要求目标网格完全被主网格覆盖。

### `DopplerSampleGenerator/config/livermore_*.json`

- `number_of_events`：该能量的入射粒子数。
- `source.energy_MeV`：标定能量。
- `source.theta_degree`、`phi_degree`：标定源方向。
- `physics.compton_model`：正式标定使用 `livermore`。
- `selection.minimum_layer_energy_MeV`：层触发阈值。
- `random_seed`：每个能量使用独立固定种子。

### `ResponseCalibration/config/calibration_config.json`

- `inputs`：五个标定样本。
- `scatter_angle_edges_degree`：散射角分箱；当前 `[0,180]` 是能量依赖的一维初版。
- `arm_bin_count`、`arm_min_degree`、`arm_max_degree`：ARM 直方图。
- `minimum_events_per_bin`、`minimum_test_events_per_bin`：训练/测试最低统计量。
- `test_fraction`：确定性留出测试集比例。
- `output_*`：参数 ROOT、比较 JSON、模型状态 JSON 和图片目录。

输出中的 `scatter_angle_bin_center_degree=90` 只是 `[0,180]` bin 的中心标签，不表示所有事件都在 90° 散射。

### `Reconstruction/config/recon_*.json`

- `input_events_file`：外部事件文件路径。
- `absolute_efficiency_file`：重采样后的效率图。
- `healpix_nside` 与能量网格：必须和 target efficiency 一致。
- `iteration_count`：LM-MLEM 迭代次数。
- `response_kernel.type`：三种模型之一。
- `response_kernel.calibration_file`：标定 ROOT 文件。
- `denominator_floor`：数值防零下限，不是物理效率 baseline。
- `event_branches`、`result_branches`：ROOT Branch 名映射。

### `KernelBenchmark/config/benchmark_config.json`

- `inputs`：三个候选重建结果。
- `model_status_json`：决定哪些模型可以参加比较。
- `calibration_comparison_json`：提供同一留出测试集上的 NLL 和 AIC/BIC。
- `truth_info_file`：真值方向和能量。
- `output_json`、`figures_directory`：集中输出位置。

### `Visualization/config/truth_info.json` 与 `plot_*.json`

- `theta_degree`、`phi_degree`、`energy_MeV`：真实源信息。
- 每个 `plot_*.json` 控制对应模型的输入、图片目录、绘图开关和拟合窗口。

## 6. 输出位置

只需复制整个 `runs/latest/`：

```text
runs/latest/
├── run_manifest.txt
├── config_snapshot/
├── efficiency/
├── calibration/
│   ├── samples/
│   ├── figures/
│   ├── doppler_response.root
│   ├── model_comparison.json
│   └── model_status.json
├── reconstruction/
├── benchmark/
└── visualization/
```

旧的 `runs/latest` 会移动到 `runs/archive/<时间戳>/`。

## 7. 何时需要 make clean

通常不需要。Make 会只重新编译变化的文件。只有怀疑目标文件来自错误依赖环境时才执行：

```bash
make clean
make configure
make all
```

`make clean` 只删除编译产物，不删除 `events.root`、`runs/latest` 或归档结果。
