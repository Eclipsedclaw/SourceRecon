# 操作说明

## 只更新 skymap 配色（已有 ROOT 结果，不重新模拟）

更新 `Quicklook/plot_raw_efficiency_map.C` 后，在服务器本工具根目录执行：

```bash
make smoke-plot
```

该命令只读取 `runs/smoke_test/raw_efficiency_master.root` 并重画三张 PNG，
不会启动 Geant4，也不需要 `make clean`、`make all` 或重新运行 `make smoke`。
图片仍保存在 `Quicklook/figures/smoke_test/`，会替换其中同名的旧图片；
若需要对照旧图，请先另外保存一份。

skymap 现在使用自己的颜色范围，不再沿用空坐标框的范围。
它应与矩形 **对数图** 同色同值：最大效率接近黄色，最小正效率接近深紫色，
零值仍留白，未模拟的后半球仍为灰色。不要直接与矩形线性图比较同一颜色，
因为线性图和对数图的颜色映射方式不同。

完整模拟输出仍使用 `make quicklook` 重画，不必重新模拟。

## 先验证此次全零修复（推荐）

将更新后的本工具源码同步到服务器同名目录，保留服务器自己的
`config/local.mk` 和已有 `runs/` 数据；不要只复制 `.cpp`，对应头文件及两个
Makefile 也必须更新。本次 Makefile 已补充头文件依赖，`make smoke` 会重新
编译受影响对象，无需手动删除 ROOT 文件。

在服务器终端执行（如果仍在 `root [数字]` 提示符，先输入 `.q`）：

```bash
cd ~/labwork/SourceRecon/EIID_CPP/raw_efficiency_map_experiment
make smoke
```

若提示缺少依赖配置，先运行一次 `make configure`，再执行 `make smoke`。

本命令使用 `Geant4_Simulation/config/smoke_config.json`：源距离仍为
5000 mm，Nside=2，只有 0.662 MeV 一个能量点。前半球含赤道共 28 个方向，
每方向 10000 个事例，共 280000 个。粗网格只用于检查流程是否正常，
不能用这次图片判断正式角分辨率。完整模拟的 `sim_config.json` 不受影响。

启动后应看到：

```text
Actual primary particle: gamma
```

结束时会打印完成事例数、有记录 hit 的事例数、ch2/ch1 分别达到阈值的
事例数、双层有效触发数和有触发的 cell 数。随后 ROOT 检查脚本自动核对
完整计数、非零触发及 `efficiency == (k/N) * cone_fraction`。通过时打印：

```text
SMOKE TEST PASSED: nonzero triggers, complete counts, raw efficiency verified.
```

如果仍无触发，`make smoke` 会以失败状态返回并保留 ROOT 文件，请提供
实际粒子名称和最后的计数摘要；不要直接扩大统计量。测试通过仅表示
模拟、计数和写盘链条工作正常，不代表效率数值已达到所需统计精度。

测试结果位于 `runs/smoke_test/raw_efficiency_master.root`，不会覆盖
原来的 `runs/raw_efficiency/raw_efficiency_master.root`。

单独画这次测试结果：

```bash
make smoke-plot
```

三张 PNG 位于 `Quicklook/figures/smoke_test/`，能量恰好为 0.662 MeV，
无需能量插值。模拟过但零计数的区域保持零；后半球标灰。

## 全零图的显示

新版即使切片全零也会生成矩形图和 skymap，图中明确标注
`All simulated pixels = 0; logarithmic scale is undefined.`。
为保持固定输出文件名，带 `_log.png` 的文件在全零时也会输出，但不使用
对数色标；白色表示零，不添加任何人为 baseline。

## 1. 配置依赖并编译

```bash
cd ~/labwork/SourceRecon/EIID_CPP/raw_efficiency_map_experiment
make configure
make all
```

## 2. 设置统计量

编辑：

```text
Geant4_Simulation/config/sim_config.json
```

其中 `grid.particles_per_cell` 是每个方向—能量 cell 的粒子数。默认仍为
100，便于直接观察零计数问题。不要把这份低统计量结果用于正式重建。

## 3. 一键重新模拟并画图

```bash
make experiment
```

也可以分开执行：

```bash
make run-simulation
make quicklook
```

输出 ROOT 文件：

```text
runs/raw_efficiency/raw_efficiency_master.root
```

输出图片：

```text
Quicklook/figures/raw_efficiency_map_E0p662_linear.png
Quicklook/figures/raw_efficiency_map_E0p662_log.png
Quicklook/figures/raw_efficiency_map_E0p662_skymap_aitoff_log.png
```

在对数图中，前半球内部未着色的白色 cell 表示 `valid_count == 0`，即未
平滑效率严格为零；灰色区域表示没有模拟的后半球。

## 4. 修改目标能量

编辑 `Quicklook/run_raw_efficiency_map.C` 中：

```cpp
const double targetEnergyMeV = 0.662;
```

如果目标能量不在格点上，工具会对相邻两个 raw-efficiency 能量层做线性
插值，但不会对方向做平滑。
