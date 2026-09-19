# EIID V8 多普勒响应架构——开发者说明

## 文档定位

本 README 面向开发人员，说明模块边界、数据契约、核心公式和扩展接口。如何修改 JSON、编译和运行请看 `MANUAL_CHN.md`。

V8 从 V7 完整复制而来，V7 目录未被修改。正式效率模拟、网格兼容器、事件翻译器和可视化模块均被保留；V8 只把原先固定宽度高斯响应升级为可标定、可替换的响应核，并增加公平比较 Voigt 与双高斯的工具链。

## 总体目录

```text
v8_doppler_response/
├── common/                    公共物理类型、HEALPix 网格、效率容器
├── SimulationSupport/         标定样本 ROOT 数据契约
├── Geant4_Simulation/         正式 Mode 0 效率图 / Mode 1 事件模拟器
├── GridResampler/             Master 效率图到重建网格的转换器
├── Translator/                原始 Geant4 Step 到精简事件的 ETL
├── DopplerSampleGenerator/    自由电子/束缚电子响应标定样本生成器
├── ResponseCalibration/       Voigt 与双高斯拟合、检验和参数写盘
├── ResponseKernel/            响应核接口、实现、插值和 ROOT 读取
├── Reconstruction/           注入响应核的 EIID + LM-MLEM
├── KernelBenchmark/           两种重建结果的端到端公平比较
├── Visualization/             V7 模型无关质量图与 ROOT 绘图
├── legacy_v3_snapshot/        历史审计快照
├── config/                    机器本地依赖配置与通用配置
├── Makefile                   总编译和工作流入口
├── configure.sh               一次性依赖发现
├── README.md / README_CHN.md  开发者文档
└── MANUAL.md / MANUAL_CHN.md  用户手册
```

每个模块都保留独立 `Makefile`、`README(.md/_CHN.md)` 和 `MANUAL(.md/_CHN.md)`；因此可以只复制、编译和使用某个模块。

## 两条互不混淆的数据流

正式探测效率和事件流仍与 V7 相同：

```text
Geant4_Simulation Mode 0
        │
        v
absolute_efficiency_master.root
        │
        v
GridResampler ───────────────> absolute_efficiency.root
                                      │
Geant4 Mode 1 ──> events.root ────────┤
raw_steps.root ─> Translator ─────────┤
                                      v
                               Reconstruction
                                      │
                                      v
                                  result.root
                                      │
                                      v
                                Visualization
```

新增的多普勒响应标定与比较流为：

```text
DopplerSampleGenerator
   ├─ free.root（自由电子对照）
   └─ livermore_<energy>.root（束缚电子标定样本）
                    │
                    v
           ResponseCalibration
             ├─ doppler_response.root
             ├─ model_comparison.json
             └─ 单分箱拟合图
                    │
                    v
              ResponseKernel
          ┌─────────┴──────────┐
          v                    v
   VoigtKernel       DoubleGaussianKernel
          │                    │
          └─────────┬──────────┘
                    v
       同一 Reconstruction / 同一事件 / 同一效率
          ├─ result_voigt.root
          └─ result_double_gaussian.root
                    │
                    v
             KernelBenchmark
```

效率图描述“来自某个方向—能量 cell 的光子被探测器有效触发的绝对概率”；响应核描述“已经给定一个事件和候选 cell 时，ARM 偏差出现的条件概率密度”。二者是不同物理量，不能互相替代。

## 新增模块职责

### SimulationSupport

`CalibrationSchema` 是样本文件的唯一 Branch/元数据命名契约。生成器和标定读取器共享它，避免字符串在两个模块中各写一遍后悄悄失配。

### DopplerSampleGenerator

复用已通过 V7 小实验验证的 Geant4 几何和事例选择：真实第一次相互作用必须位于 ch2，后续有效相互作用位于 ch1；不要求光子被完全吸收。程序同时保存 truth 级和 detector 级 ARM，后者包含同层能量加权质心与能量聚合造成的附加展宽。

`ExperimentPhysicsList` 可切换自由电子、Livermore 和 LowEP 康普顿模型。默认生产扫描包含 0.3、0.5、0.662、1.0、2.0 MeV 五个 Livermore 样本。

响应接口支持以“入射能量 + 康普顿散射角”为条件，但默认低统计标定只使用一个 `[0,180]` 角度区间；因此当前生成的第一版参数表实际上只随能量变化，不声称已标定散射角依赖。默认样本还使用同一个源方向，源方向不变性同样需要多方向闭合检验。

### ResponseCalibration

标定器按 `(incident energy, reconstructed kinematic scatter angle)` 分箱，使其与重建查询中的 `theta_energy` 一致。每个分箱通过 `event_id` 的确定性哈希划分训练集和测试集，保证输入文件顺序变化不会改变划分。

同一训练直方图同时拟合：

```text
Voigt:             Gaussian core ⊗ Lorentzian tail
Double Gaussian:   w·G(μ,σcore) + (1-w)·G(μ,σtail)
```

AIC/BIC 使用训练集似然；`test_nll` 使用未参与拟合的测试样本。ROOT 文件还保存经验三维 PDF，作为非参数基线。拟合收敛标志会写入参数树，不会被静默丢弃。

### ResponseKernel

`IResponseKernel` 是热循环中的稳定接口：

```cpp
virtual Decimal evaluate(const ResponseQuery& query) const = 0;
```

`ResponseQuery` 只含 ARM 偏差、入射能量和散射角，不依赖 `Event`、`Cell` 或求解器。当前插件：

- `FixedGaussianKernel`：V7 兼容基线；
- `VoigtKernel`：高斯核与洛伦兹尾卷积；
- `DoubleGaussianKernel`：核心和宽尾混合；
- `HistogramKernel`：经验 PDF 非参数基线。

`KernelParameterTable` 将二维参数表存成一维连续数组，在矩形能量—角度网格上双线性插值；越出标定范围时夹到最近边界，避免不受控外推。工厂负责从 JSON 选择实现。

### Reconstruction

康普顿几何仍在 `EiidResponse` 中计算：

```text
delta_theta = theta_geometry - theta_energy
q_ij = K(delta_theta, E_j, theta_energy)
a_ij = efficiency_j * q_ij
```

随后原有 LM-MLEM 使用：

```text
prediction_i = Σ_j a_ij * image_j
image_j(new) = image_j(old) / efficiency_j * Σ_i a_ij / prediction_i
```

V8 只通过构造函数向 `LmMlemSolver` 注入 `IResponseKernel`；没有复制 Voigt 版和双高斯版求解器。旧 JSON 不含 `response_kernel` 时自动退回固定高斯。

### KernelBenchmark

比较器读取两个或更多 `result.root`，计算同一真值下的峰值角误差、峰值能量误差、能量均值/宽度、R50/R68/R90，并输出统一 JSON、归一化能谱叠图和方向包含率叠图。它不参与拟合，也不改写结果。

## 保留的 V7 模块

- `common`：`Decimal`、`Vec3/Event/Cell`、`IGrid`、`HealpixGrid`、`AbsoluteEfficiencyMap`。
- `Geant4_Simulation`：各向同性绝对效率打表和精简事件生成；源球中心仍为 ch2 几何中心。
- `GridResampler`：`nearest` 与 `polygon` 可插拔策略。
- `Translator`：按 eventID 聚合 Step、同层能量加权质心、ch2→ch1 重组。
- `Visualization`：全天图、能谱、包含率、模型无关能量/方向指标和质量 JSON。

## 数据契约与防呆

- `doppler_response.root/ResponseParameters` 必须形成完整矩形的能量—散射角表；重复或缺行会被拒绝。
- 参数宽度必须有限且为正；混合权重会限制在 `[0,1]`。
- 重建读取标定表时会检查当前所选模型的收敛 Branch；任意分箱未收敛就终止，不会静默使用无效参数。
- 所有响应核返回单位为 `degree^-1` 的归一化概率密度。
- 效率网格与重建网格仍需 Nside、排序、能量轴和 cell 数完全匹配。
- 零效率 cell 仍被屏蔽；V5 Jeffreys 正则化逻辑未被响应核改动。
- 标定范围外的能量/角度采用边界值，因此生产标定应覆盖实际重建范围。
- 默认标定尚未证明响应对源的绝对天空方向不变；生产使用前应做多方向闭合检验。

## 扩展方法

增加新参数响应模型只需：

1. 实现 `IResponseKernel`；
2. 在 `ResponseKernelFactory` 注册名称；
3. 若需要拟合，新增 `IResponseFitter` 实现；
4. 不修改 `LmMlemSolver`。

增加模型评价量只修改 `KernelBenchmark`；增加普通物理图只实现 Visualization 的 `IPlotter`。这种边界保证“模型选择”和“正式重建”可以分别演进。

## 自检

`make test` 当前覆盖：公共效率容器、绝对效率估计、响应参数插值、响应归一化、共享样本 schema，以及效率加权 MLEM 的最小例子。完整 Geant4 与 ROOT 端到端运行见用户手册。
