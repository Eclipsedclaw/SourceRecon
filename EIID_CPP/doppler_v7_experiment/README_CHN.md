# Doppler V7 探索实验

这不是正式的 V8，而是从 V7 分出的一个小型消融实验。它只回答一个问题：

> 当前看到的方向和能量拖尾，有多少是束缚电子初始动量（通常称为 Doppler broadening）本身造成的？

正式目录 `v7_model_independent_metrics/` 未被修改。

## 实验变量

三组实验使用完全相同的探测器、点源、随机种子、触发条件和事件筛选，只切换 Compton 模型：

| 配置 | 模型 | 用途 |
|---|---|---|
| `config/free.json` | `G4KleinNishinaCompton` | 自由静止电子参考组，不含束缚电子初始动量 |
| `config/livermore.json` | `G4LivermoreComptonModel` | 当前正式工程使用的低能模型 |
| `config/lowep.json` | `G4LowEPComptonModel` | 可选的更完整低能模型；取决于本机 Geant4 是否提供 |

默认点源参数为：0.662 MeV、`theta=165°`、`phi=180°`、距 ch2 中心 5000 mm。这里“点源”表示空间位置固定；为节约算力，光子方向在自动包住探测器的小锥内均匀采样。每个事例的 ARM 使用其真实入射方向，所以小锥不会伪造角展宽。

发射经过定向锥重要性采样，因此输出中的 `selected_fraction` 只用于检查三组统计是否正常，**不是各向同性点源的绝对探测效率**。

## 事件定义

只有同时满足以下条件的事例才写入结果：

1. 主光子的第一次离散相互作用是在 ch2（ID 0）中的 Compton；
2. 主光子的下一次离散相互作用发生在 ch1（ID 1）；
3. ch1 中的第二次相互作用可以是 Compton，也可以是光电吸收；
4. ch2 和 ch1 都有超过阈值的宏观沉积能量；
5. 第一次 Compton 的 truth-level 运动学有实数解。

第二次之后允许继续发生任意次相互作用，也允许光子逃逸。不要求完全吸收，不要求 `e1+e2` 等于入射能量。

“一次相互作用”指主光子的一个离散 `compt`/`phot` 过程，不是一个 Geant4 Step。ch2、ch1 中所有粒子产生的沉积 Step 分别求和，并用能量加权质心得到宏观命中位置。

每个事件同时保存两套结果：

- `truth_level`：使用第一次 Compton 的真实转移能量及散射前后真实方向，主要观察 Doppler 展宽；
- `detector_level`：使用每层总沉积能量和能量加权质心，包含电子逃逸、回散和读出聚合效应。

## 一次性运行

```bash
cd ~/labwork/SourceRecon/EIID_CPP/doppler_v7_experiment
make configure
make all
make experiment
```

`make experiment` 依次运行自由电子组、Livermore 组并画比较图。

若本机 Geant4 提供 `G4LowEPComptonModel`，再运行：

```bash
make run-lowep
make compare
```

单独运行某组：

```bash
make run-free
make run-livermore
make run-lowep
```

修改追踪代码后，先用 10000 个自由电子事件做快速自检：

```bash
make smoke-free
cat output/smoke_free_summary.json
```

该目标使用 `config/smoke_free.json`，不会覆盖正式的 `free.root`。

已有 ROOT 文件时只重新画图：

```bash
make compare
```

## 输出

`output/` 中每组各有一个 ROOT 和一个计数摘要 JSON。ROOT 的 `SelectedEvents` 树保存：

- `truth_e1_MeV` 与聚合后的 `detector_e1_MeV`、`detector_e2_MeV`；
- truth 相互作用位置与 detector 能量质心位置；
- 散射前后真实光子方向；
- truth/detector 两套几何角、运动学角和 ARM；
- truth/detector 两套 EIID 反解能量与残差；
- 主光子相互作用总数及第二次相互作用类型。

`figures/` 中生成八张比较图，文件名前缀区分两层：

- `truth_*`：更接近纯 Doppler 的结果；
- `detector_*`：按真实 chamber Step 聚合后的结果；
- 每层各包含 ARM、能量残差及二者的绝对值累计分布。

`output/comparison_summary.json` 给出 FWHM、R68、R90 和尾部比例。

## 如何判断下一步

- 若 truth-level 的 Livermore 相比自由电子组明显变宽，差值就是束缚电子/Doppler 贡献的直接证据。
- 同一模型中 detector-level 相比 truth-level 的新增展宽，主要来自能量沉积和位置聚合。
- 若两层结果仍远窄于正式 V7，则正式结果的长尾还包含事件选择或响应模型失配。
- 若 LowEP 与 Livermore 差异明显，后续正式版本应把 Compton 微观模型当作系统误差来源继续研究。

不要只看高斯拟合。这个实验同时报告 FWHM、R68、R90 和尾部比例，因为 Doppler 展宽和逃逸尾通常不是高斯形状。

## 常用可调参数

三个模型 JSON 中除 `physics.compton_model` 和输出路径外，其余参数应保持相同：

- `number_of_events`：每组发射数；默认 1000000。严格筛选后的样本远少于发射数，统计不足时三组一起提高。
- `source.energy_MeV`：单能点源能量。
- `source.theta_degree`、`phi_degree`：源相对 ch2 中心的方向。
- `source.hemisphere_radius_mm`：点源到 ch2 中心的距离。
- `source.emission_cone_safety_margin_degree`：自动发射锥的额外安全边。
- `selection.minimum_layer_energy_MeV`：每层最低有效沉积能量。

比较图范围和尾部阈值在 `config/comparison.json` 中调整。
