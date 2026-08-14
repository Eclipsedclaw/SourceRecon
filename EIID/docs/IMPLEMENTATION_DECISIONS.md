# EIID 实现决策记录

## 1. 文档用途

本文件记录从两份设计基线到代码实现的可追溯决策。设计基线本身不在开发中
静默改写。凡属“待确认事项”，只能以候选配置、验证结论和明确状态记录，不能
在领域代码中写成没有来源的永久常量。

## 2. 已确认并进入阶段 1 的决策

1. 项目最低支持 Python 3.8，以兼容服务器现有 `py38` 环境。
2. 正常前向 Geant4 传播沿全局 `+Z`；相机正前方的天空来源方向为 `-Z`。
3. 正常层序为 `ch2 -> ch1 -> ch0`。
4. 数字化后 `ch1` 与 `ch2` 同时存在有效 hit 才触发；`ch0` 不参与必要触发。
5. 原始 digitized hit 不在领域/I/O 层按 layer 永久折叠。
6. 模拟和实验使用相同 `MeasuredEvent`；模拟真值放在独立可选对象中。
7. 第一版能量范围为 0.1–3.0 MeV，并在配置中显式记录。
8. 数值库内部线程默认设为 1，主要并行层是相互独立的数据集 worker。
9. 服务器日志必须同时写终端和 `.log`，并保留 Python 真实退出码。
10. 服务器唯一项目根目录为 `/home/ezqi/labwork/SourceRecon/EIID`；所有输入、
    输出、响应库、日志和 checkpoint 必须位于该目录下。

## 3. 当前候选默认值（尚非物理定案）

| 项目 | smoke 候选 | 状态 |
|---|---:|---|
| HEALPix nside | 8 | 仅基础验证；正式候选需比较 16/32 |
| 能量 bin 宽度 | 0.1 MeV | 仅基础验证；正式候选为 0.05 MeV |
| 背景 | none | 仅封闭模拟 |
| digitizer | truth | 没有实验标定前不得称为 realistic |
| ch0/ch1/ch2 阈值 | 0 MeV | 仅测试触发逻辑，不是飞行阈值 |
| worker 上限 | 5 | 实际并发必须由内存保护动态降低 |
| 系统保留内存 | 5 GiB | 服务器部署前按机器容量复核 |
| 单 worker 峰值估计 | 4 GiB | 必须用 telemetry 更新 |

## 3.1 阶段 2 输入实现决策

1. 当前 `Tree1` 仅作为 legacy 兼容输入；正式响应不能依靠它计算生成分母。
2. legacy step 按 `eventID + chamberID + pixelID` 聚合，能量求和、位置取沉积
   能量加权平均，并保存 step 数、最早时间和最早 step 序号。
3. ROOT tree、全部 branch、分块大小和 chamber/channel 映射均来自配置。
4. legacy ROOT 跨分块时暂存末尾 event，输入 eventID 倒序时明确失败。
5. `TruthDigitizer` 只用于物理检查，不代表 realistic digitizer。
6. 实验数据使用每行一个 hit 的长表，避免多通道 outer-merge 产生笛卡尔积。
7. 实验能量支持直接 MeV 和逐像素线性 ADC 标定；实际标定参数仍待提供。
8. 输入源保留全部事件，`EventIngestionPipeline` 才应用触发，并同时返回接受与
   拒绝视图。

## 3.2 阶段 3 响应实现决策

1. 重建器依赖 EventResponseModel 和 SparseEventResponse，不依赖具体
   响应库磁盘格式。
2. 条件接受概率、远场有效面积和有限距离 s_emitted 使用不同枚举、单位及
   元数据；有限距离计算显式乘 Omega/(4*pi)。
3. 当前解析 ARM 核仅是相对似然联调模型，ARM 宽度由配置显式提供，不作为
   正式归一化响应。
4. NPZ+JSON 适配器明确标记为 prototype_not_formal；它不是对待确认正式
   响应库格式的决定。
5. backscatter 不在 I/O 删除；当前正常序列核返回带原因的空响应，为未来
   R_back 保留同一接口。

## 3.3 阶段 4 运行身份与 LM-MLEM 实现决策

1. run_id 组合 UTC 微秒时间、运行类型、配置 SHA-256 前缀和随机后缀；日志、
   runs 和 response_campaign 使用同一个编号。
2. 已存在的 run_id 禁止覆盖。SUCCESS.json 最后原子写入，作为唯一完成标记；
   异常或用户中断写 FAILURE.json。
3. LM-MLEM 只消费 SparseEventResponse 和明确类型的 SensitivityMap，不读取
   响应磁盘格式。
4. 零灵敏度单元固定为零；极小事件分母、空数据集、全零更新和非有限数明确
   记录或失败，不静默产生结果。
5. 当前 stage4 小矩阵是 synthetic 软件验证，不是正式物理响应或参数定案。

## 3.4 阶段 5 端到端与绘图实现决策

1. 实验输入、触发、事件核、LM-MLEM 和输出已闭合，但解析响应仍明确标记为
   prototype_relative_likelihood_not_normalized。
2. HEALPix RING 提供纯 NumPy 后备；NESTED ordering 未安装 healpy 时明确失败。
3. 相机正前方由配置的 -Z 居中，显示向上方向单独配置，避免隐藏 roll 约定。
4. raw map 使用最近 HEALPix 像素填充栅格，不用散点；smoothed map 使用配置
   的球面高斯 sigma，并保持总强度。
5. stage5 的 nside、ARM sigma、平滑 sigma 和单位灵敏度均为 smoke 参数，
   不是正式物理定案。

## 3.5 生产响应与批处理实现决策

1. 第一版交换格式采用 `portable_npz_json_v1`：manifest + NPZ + SHA-256 +
   SUCCESS。原因是 Python 3.8 环境无需新增强制依赖，且 adapter 接口允许以后
   替换为 HDF5/Zarr；这不是把重建器绑定到 NPZ。
2. 混合核使用解析康普顿运动学、逐方向/能量 ARM 标定和同库灵敏度。响应网格
   与重建网格不同时第一版明确拒绝，不做未经验证的隐式插值。
3. `candidate_unvalidated` 可以做软件闭环但输出保持不可用于物理；只有
   `validated_physical` 才解除门禁。
4. Geant4 节点分母必须包含零沉积与未触发 primary。legacy Tree1 不满足时
   拒绝构建正式灵敏度，不用外观正常的零数组或猜测分母代替。
5. 多数据集采用独立子进程；maximum_workers 只是上限，实际并发由实时可用
   内存、保留线和单 worker 峰值估计共同决定。
6. 能谱不确定度当前为 observed Fisher 对角近似并显式记录“忽略协方差”，
   后续物理发布需用独立蒙特卡洛或 bootstrap 验证覆盖率。

## 4. 后续必须通过验证决定

- 正式 HEALPix nside 和能量网格；
- 背景模型；
- 正则化与早停参数；
- 实验逐通道/像素阈值、能量分辨、噪声和符合窗口；
- 正式 Geant4 版本、电磁物理列表、production cuts 和 step limit；
- 响应节点、插值、压缩和版本兼容；
- backscatter/pair-production 第一版响应分量；
- 高规模响应库是否从 portable NPZ+JSON 迁移到 HDF5/Zarr，以及迁移阈值；
