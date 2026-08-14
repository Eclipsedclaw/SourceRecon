# EIID 阶段 1 数据模型

## 1. 可观测对象与真值分离

`DigitizedHit` 表示电子学可观测 hit。`MeasuredEvent` 表示属于同一 gamma/符合
窗口的全部 digitized hits。模拟和实验都使用这两个对象。

模拟特有信息放在 `SimulationTruth` 中，并通过 `MeasuredEvent.observable_copy()`
得到不携带真值的事件。未来重建入口只接收可观测视图，验证分析器才允许读取
真值。

## 2. 不可逆处理边界

领域对象保留同层多像素 hit、原通道、像素、时间、不确定度和质量标志。
正常序列、backscatter、合并交互等属于候选拓扑解释，不得覆盖原 hit。

## 3. 坐标

- `detector_stack_direction = (0,0,+1)`：从前层向后层；
- `camera_boresight_source_direction = (0,0,-1)`：相机正前方天空来源；
- `source_direction = -propagation_direction`。

正常事件中，若第一、第二交互为 `r1`、`r2`，来源侧康普顿轴为：

\[
\mathbf a=-\frac{\mathbf r_2-\mathbf r_1}{\|\mathbf r_2-\mathbf r_1\|}.
\]

## 4. 触发

触发只由 `TriggerPolicy` 决定。`valid_hit` 同时要求 hit 自身可用且能量达到该
通道配置阈值。若配置符合窗口，还要求 ch1/ch2 至少存在一对 hit 满足时间差。
ch0 不改变触发成立与否。

## 5. Geant4 legacy 输入边界

当前 `Tree1` 的一行是 step。正沉积 step 先聚合为 `DetectorDeposit`，然后交给
`Digitizer` 生成 `DigitizedHit`。由于 `Tree1` 没有零 hit primary，使用该输入
得到的 `observed_event_count` 不能作为响应效率的生成分母；数据集 summary 会
固定记录 `primary_denominator_complete=false`。

## 6. 实验输入

实验 CSV/TSV 每行表示一个 hit，不把三通道先合成宽表。相同 EventID 的所有
通道和像素行组成 `MeasuredEvent`。输入支持直接 MeV，或通过逐像素线性标定
`E_keV = slope * ADC + intercept` 转换。实验事件的 `truth` 永远为 `None`。
