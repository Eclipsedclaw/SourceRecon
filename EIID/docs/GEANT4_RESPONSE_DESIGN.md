# Geant4 响应模拟与响应库设计说明

## 1. 文档目的

本文档规定 Geant4 在 EIID 项目中的职责、当前模拟程序的可用基础、需要补充的 ROOT 输出、受限立体角抽样、数字化、触发、响应库构建和验证方案。

核心原则是：

> Geant4 是离线响应数据生产工具，不是 EIID 迭代运行时的一部分。

EIID 在重建实验数据时读取已经生成并验证过的响应库，不应为每个观测事件实时运行 Geant4。

本文档只描述设计；当前阶段不修改 `compton_satellite_sim`。

---

## 2. 当前 Geant4 工程审查结果

当前工程位于：

```text
D:\CodexForSR\compton_satellite_sim
```

与现有 90 组 ROOT 数据直接对应的主要版本为：

```text
compton_camera_pixel
```

### 2.1 探测器几何

当前像素化模型包括：

- 第一层 14×14 YSO，单像素约 3.0 mm × 3.0 mm，厚 3.0 mm；
- 第二层 14×14 YSO，单像素约 3.0 mm × 3.0 mm，厚 3.0 mm；
- YSO 像素节距约 3.36 mm，包含 BaSO₄ 反射材料；
- 最后一层整块 LYSO，横向约 47.04 mm × 47.04 mm，厚 6.0 mm；
- 每个探测层附近存在 Si、FR4 等非灵敏材料；
- 前两层结构间距默认约 25 mm；
- 第二层与 LYSO 间距默认约 35 mm。

### 2.2 通道映射

| chamberID | 几何层 | 算法通道 |
|---:|---|---|
| 0 | 第一层 YSO | ch2 |
| 1 | 第二层 YSO | ch1 |
| 2 | 厚 LYSO | ch0 |

卫星记录事件的必要条件是数字化后 ch1、ch2 同时存在有效 hit。ch0 是否有 hit不影响触发成立。

### 2.3 当前粒子源

程序使用 `G4GeneralParticleSource`，宏文件可配置粒子、位置、能量和方向。当前 ROOT 没有独立的逐事件 primary truth 表；当一个文件内能量和方向固定时，可以从宏文件和文件名推断，但这种方式不适合正式响应库。

### 2.4 当前物理列表

`compton_camera_pixel/exampleB2a.cc` 当前实际启用 `FTFP_BERT` 并注册 `G4StepLimiterPhysics`。仓库中的自定义 `MyPhysicsList` 存在，但未在主程序中启用。

正式响应生产必须记录：

- Geant4 版本；
- 物理列表名称和设置；
- production cut；
- 随机数引擎和种子；
- 几何版本和材料参数。

不应在没有对照验证的情况下更换物理列表。

### 2.5 当前 ROOT `Tree1`

当前 `Tree1` 每行记录灵敏探测体中的一个 Geant4 step，包含 eventID、trackID、parentID、chamberID、pixelID、前后位置、动量、沉积能量、粒子名和过程名等。

重要解释：

- 一行不是一个实验 hit；
- 同一事件、同一像素内可有许多 gamma、电子和次级粒子 step；
- 必须经过聚合和数字化才能得到实验可读出的 hit；
- 没有在灵敏体中留下记录的事件不会出现在 `Tree1`；
- 因而仅凭 `Tree1` 无法得到总生成事件数或零响应事件数；
- `Process_post` 通常比 `Process_pre` 更适合判断结束当前 step 的物理过程；
- 当前 `kineticEnergy_MeV` 实际记录的是 post-step kinetic energy；
- 当前 `angle_deg` 是单个 step 的前后动量夹角，不是 gamma 的全局入射极角。

### 2.6 DSSD 分支的可参考功能

`compton_camera_DSSD` 已尝试输出事件级 `Efficiency` 树，包含初级能量、是否有沉积和总沉积是否超过初级能量的 95%。这一思路可参考，但不足以直接用于本项目，因为它没有逐层能量、ch1+ch2 触发、方向、backscatter 和数字化信息。

---

## 3. Geant4 与 EIID 的系统边界

推荐数据流：

```text
Geant4 物理输运
    ↓
PrimaryTruth / InteractionTruth / DetectorDeposit
    ↓
可配置数字化模型
    ↓
ch1+ch2 触发模拟
    ↓
响应统计与参数化
    ↓
版本化响应库
    ↓
EIID 重建程序
```

Geant4 负责：

- 材料中的物理相互作用；
- 次级粒子输运；
- 真实沉积能量和位置；
- 真实相互作用顺序；
- gamma 逃逸、backscatter、全吸收和电子对产生真值。

Geant4 不应永久硬编码：

- 实验能量分辨；
- 通道阈值；
- 电子学噪声；
- 时间符合窗口；
- 串扰和饱和；
- 飞行触发策略。

这些易变化因素优先放在独立、可配置的数字化与触发模块中，使实验标定更新后无需重跑全部粒子输运。

---

## 4. 模拟模式

响应生产程序至少支持三种模式。

### 4.1 有限距离点源模式

用于：

- 实验室放射源；
- 0.5 m、1 m、2 m 等现有模拟；
- 计算相对于源总发射 gamma 数的绝对探测概率；
- 验证距离和偏轴位置影响。

采用用户确认的方案：不做全天球各向同性低效抽样，而只在完全覆盖相机的立体角内均匀发射，并用统计权重恢复全天球归一化。

### 4.2 远场平行束响应模式

用于：

- 宇宙远场源；
- 构造方向相关有效面积；
- 构造 \(R(d\mid\Omega,E)\) 的方向响应；
- 避免有限距离光束发散与距离依赖。

在与入射方向垂直或经过严格归一化的参考平面上均匀产生平行 gamma。输出以有效面积或入射通量响应表述，不与有限点源的 \(\Omega/4\pi\) 探测概率混为同一单位。

### 4.3 成像验证模式

用于生成独立测试数据：

- 单点源和偏轴源；
- 多点源；
- 连续谱；
- 扩展源和不规则源；
- 含 background/backscatter 的混合样本。

响应标定样本与成像验证样本必须分开，避免用同一蒙特卡洛随机样本同时训练和验证响应。

---

## 5. 受限立体角抽样

### 5.1 基本公式

设有限距离点源原本向完整 \(4\pi\) 各向同性发射。模拟只在覆盖相机的区域 \(C\) 内均匀抽样，区域立体角为 \(\Omega_C\)。如果区域外的 gamma 不可能产生被接受事件，则：

\[
s_{\rm emitted}(E)=
\frac{\Omega_C}{4\pi}
\frac{N_{\rm accepted}}{N_{\rm generated}}.
\]

其中：

- \(N_{\rm generated}\)：在受限立体角内实际生成的 gamma 数；
- \(N_{\rm accepted}\)：经过数字化、ch1+ch2 触发及质量筛选的事件数；
- \(s_{\rm emitted}\)：相对于源向全天球总发射 gamma 数的探测概率。

对于半张角为 \(\alpha\) 的圆锥：

\[
\Omega_C=2\pi(1-\cos\alpha),
\qquad
\frac{\Omega_C}{4\pi}=\frac{1-\cos\alpha}{2}.
\]

### 5.2 对立体角均匀，而不是对极角均匀

圆锥内正确抽样为：

\[
\phi\sim U(0,2\pi),
\qquad
\cos\theta\sim U(\cos\alpha,1).
\]

不得简单使用 \(\theta\sim U(0,\alpha)\)，否则角分布会产生偏差。

使用 GPS 时应采用正确的 isotropic/angular-limited 配置或经过验证的用户分布，并处理局部坐标旋转。必须特别验证 GPS 的方向符号：传播方向和天空来源方向相反，且 GPS 局部 \(\theta=0\) 的默认方向约定不能凭直觉使用。

### 5.3 一般重要性权重

每个 primary 建议记录：

\[
w_i=\frac{p_{\rm target}(\Omega_i,E_i)}
{q_{\rm generation}(\Omega_i,E_i)}.
\]

对于目标分布为全天球各向同性、生成分布为锥内均匀的情况：

\[
w_i=\frac{\Omega_C}{4\pi}.
\]

虽然此时所有事件权重相同，仍应把权重和生成概率写入元数据或 primary tree，以支持未来的方向加密、不同锥角合并和非均匀能量抽样。

### 5.4 覆盖范围与安全余量

发射区域必须覆盖所有可能产生有效事件的路径，而不仅是晶体正面：

- 完整探测器外轮廓；
- 斜入射侧面投影；
- Si、FR4、BaSO₄ 和未来结构；
- 先在非灵敏结构散射再进入晶体的路径；
- 几何和数值误差。

圆锥半角应采用：

\[
\alpha_{\rm gen}=\alpha_{\rm minimum}+\alpha_{\rm margin}.
\]

验证方法：将锥角增加 20%–30%，重新计算加权后的 \(s_{\rm emitted}\)。若在统计误差内不变，说明原锥完整；若明显增加，说明原锥漏掉了有效路径。

### 5.5 非圆形区域

相机投影为方形时，可以使用保守圆锥，也可以使用矩形角域。对一般角域：

\[
\Omega=(\phi_{\max}-\phi_{\min})
\,(\cos\theta_{\min}-\cos\theta_{\max}).
\]

第一版优先使用容易验证的保守圆锥；只有在模拟效率确有需要时再改为紧致的矩形或多边形角域。

---

## 6. 必须区分的灵敏度定义

### 6.1 相对于源总发射量

\[
s_{\rm emitted}(E,\Omega_{\rm source},r)
=
\frac{\text{被记录事件数}}
{\text{源向 }4\pi\text{ 发射的 gamma 总数}}.
\]

它依赖源距离 \(r\)，适用于实验室点源、源活度和绝对探测效率。受限圆锥模拟需要乘 \(\Omega_C/4\pi\)。

### 6.2 相对于相机处入射通量

远场天体响应通常使用有效面积：

\[
A_{\rm eff}(E,\Omega)
=A_{\rm gen}
\frac{N_{\rm accepted}}{N_{\rm generated}}.
\]

其中 \(A_{\rm gen}\) 是参考生成平面面积。这里通常不乘 \(\Omega_C/4\pi\)，因为输入量已经是相机位置处的通量。

### 6.3 EIID 中的 \(s(\Omega,E)\)

EIID 的灵敏度必须在响应库中携带单位和归一化定义。第一版应同时保存：

- 条件探测/触发概率；
- 有效面积 \(A_{\rm eff}\)；
- 有限距离点源的 \(s_{\rm emitted}\)（如该模式被模拟）。

重建配置必须明确选择哪一种物理归一化，禁止仅使用变量名 `s` 而不记录含义。

---

## 7. 新 ROOT 输出设计

建议保留现有 `Tree1` 的兼容读取能力，同时新增结构清晰的树。字段名、单位和版本必须在 ROOT 或伴随 manifest 中记录。

### 7.1 `RunMeta`

每个 run 一行：

- schema_version；
- run_id、dataset_id；
- Geant4 version；
- physics list 和 production cuts；
- geometry version/hash；
- 材料与层间距关键参数；
- primary particle；
- source mode；
- 能量分布及参数；
- 位置分布及参数；
- 角分布、锥轴、锥角、\(\Omega_C\)；
- target PDF、generation PDF 或统一权重；
- 总生成事件数；
- 随机数引擎和种子；
- 输出选项；
- 代码 commit/hash（若可用）。

### 7.2 `PrimaryTruth`

每个生成 event 必须有一行，即使它没有任何沉积：

- eventID；
- particle/PDG；
- initial_energy_MeV；
- vertex_x/y/z_mm；
- momentum_direction_x/y/z；
- source_direction_x/y/z；
- theta/phi（明确坐标系）；
- generation_pdf；
- target_pdf；
- event_weight。

### 7.3 `DetectorDeposit`

建议直接输出或由后处理生成紧凑沉积表：

- eventID；
- chamberID、channel、pixelID；
- total_edep_MeV；
- earliest_time_ns；
- energy_weighted_position；
- step_count；
- contributing_track_count。

它是物理沉积聚合结果，不包含能量展宽和阈值。

### 7.4 `InteractionTruth`

记录主要 gamma 及关键次级粒子的相互作用，而不是所有电子电离 step：

- eventID、trackID、parentID、stepID；
- particle；
- volume/layer/channel；
- pre/post position；
- pre/post kinetic energy；
- process；
- momentum direction；
- chronological interaction index；
- boundary/escape/termination flags。

### 7.5 `EventSummary`

每个 event 一行：

- primary energy/direction；
- ch2/ch1/ch0 真值总沉积；
- 每层命中像素数；
- 是否有真值沉积；
- 数字化后每层能量和像素数；
- ch2/ch1/ch0 是否超过阈值；
- `trigger_ch1_ch2_truth`；
- `trigger_ch1_ch2_digitized`；
- total deposited energy；
- escaped primary/secondary gamma energy（可获得时）；
- `is_full_absorption_truth` 及判据；
- has_compton、has_photoelectric、has_pair_production；
- true layer sequence；
- is_backscatter_truth；
- is_normal_forward_truth；
- event topology；
- final acceptance 和 rejection reason bitmask。

### 7.6 `StepTruth`（可选）

保留详细 step 树用于调试。大规模响应生产时允许关闭或仅抽样保存，以避免 ROOT 体积和 I/O 成为瓶颈。

---

## 8. 数字化模型

数字化模块建议在 Python/C++ 独立组件中实现，并使用版本化配置。处理顺序：

1. 按 eventID、channel、pixelID 合并 Geant4 step 沉积。
2. 计算能量加权位置或采用像素中心。
3. 应用逐通道能量分辨函数。
4. 加入电子学噪声。
5. 应用逐通道/像素阈值。
6. 应用时间符合窗口。
7. 可选加入串扰、饱和、死时间和坏道。
8. 生成统一 `DigitizedEvent`。

必须支持两种模式：

- **truth digitizer**：无展宽、低阈值，用于物理响应检查；
- **realistic digitizer**：使用实验标定参数，用于预测飞行数据。

响应库必须注明使用的 digitizer version，不能把不同数字化条件生成的响应混用。

---

## 9. 触发与事件接受

触发模型：

```text
trigger = valid_hit(ch1) AND valid_hit(ch2)
```

其中 `valid_hit` 必须基于数字化后的能量、时间和阈值，而不是简单判断 Geant4 沉积是否大于零。

Geant4 输出阶段不得删除未触发事件，因为它们是计算效率分母和理解损失机制所必需的。响应构建阶段为每个事件记录：

- 是否通过触发；
- 是否通过后续质量筛选；
- 首个失败原因；
- 完整 rejection bitmask。

触发效率至少拆分为：

\[
\epsilon_{\rm geom},\quad
\epsilon_{\rm interaction},\quad
\epsilon_{\rm trigger},\quad
\epsilon_{\rm selection}.
\]

这样可判断效率损失来自几何、物理相互作用、电子学阈值还是算法筛选。

---

## 10. backscatter、逃逸和高能过程

### 10.1 backscatter

必须根据真实相互作用时间和 gamma 方向记录：

- 首次相互作用层；
- 后续层序；
- z 方向是否反转；
- 正常序列或 backscatter 序列编码；
- 数字化后是否仍可辨认该序列。

第一版 EIID 可以暂不建立完整 backscatter 核，但响应库必须统计其在 ch1+ch2 触发样本中的比例，并保留未来增加 \(R_{\rm back}\) 的数据。

### 10.2 逃逸和全吸收

全吸收不能仅由“ch0 有 hit”判断。至少同时保存：

- primary 初始能量；
- 所有灵敏体总沉积；
- 所有探测器材料总沉积（若统计）；
- 离开世界/几何的 gamma 能量；
- 真值全吸收标签；
- 数字化后是否落入全能峰窗口。

真值全吸收与实验上的 photopeak selection 是两个不同标签。

### 10.3 电子对产生

能量范围延伸到 3 MeV，超过 1.022 MeV 后必须记录 pair production、电子/正电子和 511 keV 湮灭 gamma。第一版可以将其作为独立拓扑或 outlier，但响应生产不能忽略这一物理通道。

---

## 11. 响应扫描方案

### 11.1 能量范围

固定覆盖 0.1–3.0 MeV。具体能量节点待确认，但应满足：

- 低能段变化较快处适当加密；
- 覆盖现有 0.3、0.4、0.5、0.6、0.662、0.8、1.0、1.2、1.5 MeV；
- 在 1.022 MeV 附近增加节点；
- 高能段延伸到 3.0 MeV；
- 支持对响应变化剧烈区域自适应补点。

不要求 Geant4 每 0.01 MeV 跑一套大样本；可在经过验证的能量节点间插值，但插值误差必须独立评估。

### 11.2 方向范围

- 响应至少覆盖相机正前方目标视场；
- 使用 HEALPix 或明确的极角—方位角节点；
- 方形像素阵列不具有严格旋转对称性，不能只扫描极角而忽略方位角；
- 中心、水平 ±15°、垂直 ±15° 数据可作为早期验证，而不是完整响应网格。

### 11.3 事件数量

每个节点的生成量不应只固定为同一数字。建议根据目标统计误差自适应运行：

- 对低触发效率节点增加事件；
- 以关键拓扑或接受事件数达到阈值作为停止条件；
- 保存 binomial/weighted Monte Carlo 统计误差；
- 响应表同时存储有效样本量。

---

## 12. 响应库内容

响应构建器从 Geant4 truth、数字化和触发结果生成版本化库，至少包含：

- \(s(\Omega,E)\) 及其单位和统计误差；
- \(A_{\rm eff}(\Omega,E)\)；
- 有限距离模式的 \(s_{\rm emitted}\)；
- ch1+ch2 触发效率；
- 2-hit、3-hit、多像素等拓扑概率；
- 正常层序/backscatter 概率；
- 全吸收/逃逸概率；
- 各通道能量沉积分布；
- 条件逃逸能量分布；
- ARM 或更完整方向残差分布；
- 位置和能量响应参数；
- pair-production/outlier 比例；
- 插值网格和有效支持范围；
- 响应版本、几何版本、物理列表和 digitizer version。

第一版推荐使用“解析康普顿核 × 蒙特卡洛标定修正”的混合响应，避免直接存储不可管理的稠密高维矩阵。

---

## 13. 批处理与文件组织

建议工作流：

```text
generate_simulation_manifest.py
    ↓
generate_macros.py
    ↓
Geant4 executable + unique macro
    ↓
unique ROOT + run manifest
    ↓
digitize_events.py
    ↓
build_response.py
    ↓
validate_response.py
```

每个 run 必须使用唯一输出名，不依赖运行后手工重命名 `b1output.root`。推荐目录：

```text
response_campaign/
├─ campaign_manifest.json
├─ macros/
├─ raw_root/
├─ digitized/
├─ response_library/
├─ validation/
└─ logs/
```

批处理要求：

- 可恢复和跳过已完整 run；
- 用完成标记区分完整文件与中断文件；
- 检查 ROOT 树、行数和元数据后才标记成功；
- 并行度受内存和 I/O 限制；
- 随机种子不可在 worker 间重复；
- 日志记录命令、主机、开始/结束时间和退出码。

---

## 14. 验证与质量控制

### 14.1 几何和方向

- 可视化三层、死材料和源位置。
- 检查 chamberID/channel 映射。
- 检查 primary 动量方向与预期天空方向符号。
- 检查锥内 \(\cos\theta\) 和 \(\phi\) 分布。
- 检查源锥是否覆盖完整几何。

### 14.2 能量守恒

按 event 检查：

\[
E_{\rm primary}
\approx E_{\rm deposit}+E_{\rm escaped}+E_{\rm rest/secondary}
\]

误差和未计入项必须有明确解释。

### 14.3 立体角归一化

- 使用不同锥角重复模拟；
- 乘 \(\Omega_C/4\pi\) 后的 \(s_{\rm emitted}\) 应一致；
- 小规模全天球各向同性模拟可作为独立对照；
- 记录加权有效样本量和统计误差。

### 14.4 响应闭环

- 用响应库重建独立 Geant4 验证数据；
- 检查真值覆盖、能谱和方向偏差；
- 检查插值节点之间的性能；
- 比较 truth digitizer 和 realistic digitizer；
- 对比现有 SOE 和新 EIID。

---

## 15. 现有 90 组数据的定位

现有数据覆盖约 0.3–1.5 MeV、若干距离和中心/偏轴方向，可继续用于：

- 验证 ROOT step 聚合；
- 验证 ch1+ch2 触发逻辑；
- 统计现有方向和能量下的事件类别；
- 开发简化或混合响应；
- 对比 SOE 与 EIID 的早期结果。

若每个文件确实生成 1000 万个 event，可临时由外部配置提供分母。但由于缺少逐事件 primary truth 和零 hit 记录，它们不能独立承担完整 0.1–3.0 MeV、完整方向范围的正式响应库。

---

## 16. 已确定决策

1. Geant4 只负责离线响应生产，不嵌入 EIID 迭代。
2. 基础几何以当前 `compton_camera_pixel` 为起点，不在缺少验证时随意更换。
3. 卫星触发为数字化后 ch1+ch2 同时有有效 hit。
4. 所有生成事件都必须计入分母；未触发事件不能在 Geant4 输出阶段消失。
5. 有限距离点源采用覆盖相机的受限立体角均匀抽样。
6. 计算相对于总发射量的 \(s_{\rm emitted}\) 时乘 \(\Omega_C/4\pi\)。
7. 同时保留远场有效面积定义，不与有限距离绝对效率混用。
8. 每个 primary 记录真实能量、方向、位置和生成权重。
9. backscatter 第一版可暂不专门重建，但真值和接口必须保留。
10. 能量响应覆盖 0.1–3.0 MeV。

---

## 17. 待确认事项

1. 正式响应使用的 Geant4 版本和电磁物理列表。
2. production cuts、step limit 和材料参数验证。
3. 每层实际能量阈值、分辨率、噪声和时间符合窗口。
4. 源锥的安全余量及是否需要考虑完整卫星平台。
5. 远场参考生成平面的大小和方向归一化。
6. 能量节点、方向节点和每节点目标统计量。
7. `InteractionTruth` 的压缩程度和 `StepTruth` 的保存比例。
8. 第一版响应库格式（NPZ/HDF5/Zarr/ROOT 或组合）。
9. backscatter 和 pair-production 在第一版响应中的具体处理。

这些事项应通过小规模试运行、封闭测试和实验标定逐项决定。

---

## 18. 主要参考依据

1. Geant4 Collaboration, [General Particle Source](https://geant4.web.cern.ch/documentation/dev/bfad_html/ForApplicationDevelopers/GettingStarted/generalParticleSource.html)：位置、能量、角分布和 GPS 方向约定。
2. Geant4 Collaboration, [Event Biasing Techniques](https://geant4.web.cern.ch/documentation/dev/bfad_html/ForApplicationDevelopers/Fundamentals/biasing.html)：受限相空间和重要性抽样的工具背景。
3. D. Xu and Z. He, [Gamma-ray energy-imaging integrated spectral deconvolution](https://doi.org/10.1016/j.nima.2007.01.171), Nuclear Instruments and Methods in Physics Research A 574 (2007) 98–109：EIID 前向模型、响应函数和联合能量—方向反卷积的原始依据。

外部文献用于确定方法和术语；本相机的几何、触发、数字化和归一化仍以本项目实际配置与验证结果为准。
