# EIID V8 多普勒响应架构——中文用户手册

## 文档定位

本 MANUAL 面向程序使用者：告诉你改哪个 JSON、执行什么命令、得到什么文件。类和源文件设计请看 `README_CHN.md`。

## 目录速览

```text
v8_doppler_response/
├── Geant4_Simulation/       正式效率图和事件模拟
├── GridResampler/           效率网格转换
├── Translator/              原始 Step 翻译
├── DopplerSampleGenerator/  多普勒标定样本
├── ResponseCalibration/     Voigt/双高斯拟合
├── ResponseKernel/          响应模型库
├── Reconstruction/          EIID + LM-MLEM
├── KernelBenchmark/         模型结果比较
├── Visualization/           常规物理画图
├── common/                  公共网格与类型
├── SimulationSupport/       样本格式契约
├── config/                  机器本地配置
├── Makefile                 总入口
└── configure.sh             依赖探测
```

## 首次配置与编译

服务器每个项目副本只需配置一次：

```bash
cd ~/labwork/SourceRecon/EIID_CPP/v8_doppler_response
make configure
make show-config
make all
make test
```

要求：支持 C++20 的 `g++`、GNU Make、ROOT、HEALPix C++、nlohmann/json；模拟相关模块还需 Geant4。`make configure` 会把绝对路径写入 `config/local.mk`，以后新终端不必手工 `export LD_LIBRARY_PATH`。

只编译单个模块：

```bash
make simulation
make resampler
make sample-generator
make response-calibration
make response-kernel
make reconstruction
make kernel-benchmark
make visualization
```

也可进入模块目录直接 `make`。模块仍从 `../config/local.mk` 读取统一依赖。

## 最推荐：完整比较 Voigt 与双高斯

准备好正式的 `events.root` 和 `absolute_efficiency.root` 后，在 V8 根目录执行：

```bash
make response-study
```

它依次执行：

```text
五能量 Livermore 样本
  → 响应标定（两种拟合）
  → Voigt 重建
  → 双高斯重建
  → 端到端比较
```

该命令计算量很大，因为默认生成 5 × 1,000,000 个 Geant4 初级粒子。建议第一次先按下面的分步方式运行。

## 分步运行新工作流

### 1. 快速生成单个样本

```bash
make run-sample-livermore
```

使用 `DopplerSampleGenerator/config/livermore.json`，默认 0.662 MeV。自由电子对照：

```bash
make run-sample-free
```

正式五能量扫描：

```bash
make run-sample-grid
```

对应 0.3、0.5、0.662、1.0、2.0 MeV 五个 JSON。可以先把各 JSON 的 `number_of_events` 改小做连通测试，再恢复生产统计量。

这五个默认配置使用同一个源方向。当前默认散射角只有一个 `[0,180]` 全局分箱，所以第一版响应表只标定能量依赖。用于正式物理结果前，应复制这些 JSON，改变 `source.theta_degree` 和 `source.phi_degree` 做多方向闭合检验。

### 2. 标定响应

```bash
make calibrate
```

读取 `ResponseCalibration/config/calibration_config.json`，输出：

```text
doppler_response.root
ResponseCalibration/output/model_comparison.json
ResponseCalibration/figures/response_e*_a*.png
```

若只生成了一个样本，请把 `inputs` 列表暂时改成只包含该文件，并将散射角分箱设宽；否则缺失文件或低统计分箱会被明确拒绝。

### 3. 分别重建

```bash
make reconstruct-voigt
make reconstruct-double-gaussian
```

分别使用：

```text
Reconstruction/config/recon_voigt.json
Reconstruction/config/recon_double_gaussian.json
```

输出 `result_voigt.root` 和 `result_double_gaussian.root`。两次使用同一 `events.root`、同一效率图、同一网格和同一迭代次数。

### 4. 比较结果

```bash
make benchmark
```

输出：

```text
KernelBenchmark/output/kernel_benchmark.json
KernelBenchmark/figures/kernel_energy_comparison.png
KernelBenchmark/figures/kernel_direction_comparison.png
```

### 5. 用普通可视化模块查看某一个结果

修改 `Visualization/config/plot_config.json` 中的 `input_root_file`，指向 `result_voigt.root` 或 `result_double_gaussian.root`，然后：

```bash
make run-visualization
```

## 新配置文件参数

### DopplerSampleGenerator/config/*.json

| 参数 | 含义 |
|---|---|
| `experiment_name` | 本次样本标签 |
| `random_seed` | 正整数随机种子 |
| `number_of_events` | 发射初级粒子数 |
| `physics.compton_model` | `free`、`livermore` 或可用时的 `lowep` |
| `physics.atomic_relaxation` | 是否启用原子退激发 |
| `source.particle_name` | 默认 `gamma` |
| `source.energy_MeV` | 单能点源能量 |
| `source.theta_degree/phi_degree` | 点源相对 ch2 中心的方向 |
| `source.hemisphere_radius_mm` | 点源到 ch2 几何中心的距离；仍是点源，不是体源半径 |
| `source.emission_cone_safety_margin_degree` | 自动包围探测器锥的附加余量 |
| `environment.world_material` | World 材料，通常 `G4_Galactic` |
| `environment.world_margin_mm` | World 边界额外余量 |
| `selection.front_chamber_id` | ch2，当前必须为 `0` |
| `selection.rear_chamber_id` | ch1，当前必须为 `1` |
| `selection.minimum_layer_energy_MeV` | 每层最小沉积阈值 |
| `output.root_file/tree_name` | 样本 ROOT 路径和 Tree 名 |
| `output.summary_json` | 选择计数摘要 |

相对路径以当前 JSON 所在目录为基准。

### ResponseCalibration/config/calibration_config.json

| 参数 | 含义 |
|---|---|
| `inputs[]` | 一个或多个标定 ROOT 文件 |
| `inputs[].tree` | 默认 `SelectedEvents` |
| `inputs[].level` | `truth` 只看本征多普勒；`detector` 包含读出聚合，正式重建推荐后者 |
| `inputs[].compton_model` | 必须与 ROOT 元数据匹配；正式标定使用 `livermore` |
| `output_root_file` | 响应参数 ROOT 文件 |
| `output_parameter_tree` | 参数 Tree 名，默认 `ResponseParameters` |
| `output_histogram_name` | 经验三维 PDF 名 |
| `output_comparison_json` | AIC/BIC/test NLL 摘要 |
| `figures_directory` | 单分箱拟合图目录 |
| `scatter_angle_edges_degree` | 散射角分箱边界，严格递增；默认 `[0,180]` 是一个全局分箱 |
| `arm_bin_count` | ARM 直方图格数 |
| `arm_min_degree/max_degree` | 拟合与经验 PDF 的 ARM 范围 |
| `minimum_events_per_bin` | 训练集最低统计；不足直接报错 |
| `minimum_test_events_per_bin` | 独立测试集最低统计；不足直接报错，不拿训练集冒充测试集 |
| `test_fraction` | 测试集比例，必须在 `(0,0.5)` |

默认较低的 `minimum_events_per_bin` 只是防止小实验完全无法运行。正式发表结果应提高样本数和最低统计，并检查每张拟合图及收敛标志。

### Reconstruction/config/recon_*.json

V7 原有路径、网格、迭代、Branch 和 `denominator_floor` 参数保持不变。新增：

| 参数 | 含义 |
|---|---|
| `response_kernel.type` | `fixed_gaussian`、`voigt`、`double_gaussian`、`histogram` |
| `response_kernel.fixed_sigma_degree` | 仅固定高斯使用 |
| `response_kernel.calibration_file` | `doppler_response.root` 路径 |
| `response_kernel.parameter_tree` | Voigt/双高斯参数树 |
| `response_kernel.histogram_name` | 经验 PDF 名 |

旧配置只含 `response_sigma_degree` 仍可运行，会自动选择固定高斯。

### KernelBenchmark/config/benchmark_config.json

| 参数 | 含义 |
|---|---|
| `inputs[]` | 待比较结果列表 |
| `label` | 图例名称 |
| `kernel_type` | 摘要中记录的模型名 |
| `file/tree` | 结果 ROOT 和 Tree |
| `truth_info_file` | 真值方向与能量 JSON |
| `output_json` | 数值比较结果 |
| `figures_directory` | 叠图目录 |

## 保留的正式 V7 工作流

生成 Master 绝对效率：

```bash
make run-simulation SIM_CONFIG=config/sim_config.json
```

配置中的 `mode=0` 写效率，`mode=1` 写事件。源位置始终为：

```text
source_position = ch2_center + hemisphere_radius_mm * direction
```

转换效率网格：

```bash
make resampler
./GridResampler/grid_resampler GridResampler/config/resampler_config.json
```

翻译原始 Step：

```bash
make translator
./Translator/eiid_translator Translator/config/translator_config.json
```

使用固定高斯兼容模式重建：

```bash
make reconstruction
./Reconstruction/EIID_Recon_V8 Reconstruction/config/recon_config.json
```

各旧配置的所有参数仍在各模块 `MANUAL_CHN.md` 中逐项说明。

## 手动调整 Makefile / 依赖

优先重新配置，而不是逐个改 Makefile：

```bash
ROOT_CONFIG=/path/to/root-config \
GEANT4_CONFIG=/path/to/geant4-config \
EIID_DEPS_PREFIX=/path/to/root-env \
make configure
```

确需手动修改时，只编辑根目录 `config/local.mk`，常用项为：

```makefile
PROJECT_CXX_STANDARD := c++20
CXX := /usr/bin/g++
ROOT_CONFIG := /absolute/path/root-config
GEANT4_CONFIG := /absolute/path/geant4-config
HEALPIX_CFLAGS := -I/absolute/path/include/healpix_cxx
HEALPIX_LIBS := -L/absolute/path/lib -lhealpix_cxx -lcxxsupport
JSON_CFLAGS := -I/absolute/path/include
EIID_RPATH_FLAGS := -Wl,--disable-new-dtags -Wl,-rpath,/absolute/path/lib
```

不要把 `config/local.mk` 复制到另一台机器；路径是机器专属的。

## 常见错误

- `missing config/local.mk`：在根目录运行 `make configure`。
- `cannot open shared object file`：重新 `make configure && make clean && make all`，不要混用另一套 Geant4 动态库。
- `Calibration bin ... contains only ...`：先看程序打印的实际角度覆盖；合并不可达分箱或增加样本，不要用伪造数据填补空区间。
- `response rows do not form a complete rectangular grid`：每个能量必须拥有同一组散射角中心。
- `Cannot open event/efficiency file`：路径相对于对应 JSON，不相对于当前终端目录。
- `event cannot be explained`：检查事件覆盖、效率零区、响应标定范围和事件单位，而不是随意给所有 cell 加常数。
- 拟合 `converged=false`：不要直接用于正式重建；先检查样本统计、ARM 范围和分箱。
