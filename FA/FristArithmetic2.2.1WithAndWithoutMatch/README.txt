README.txt
============================================================
三层康普顿相机事件构建、Geant4 监督训练与未知能源成像程序说明
============================================================

本文档面向第一次接触本项目的同学。即使不了解此前的调试过程，
也应能通过本文理解：

    1. 项目想解决什么问题；
    2. ROOT 文件中的一行数据代表什么；
    3. 三层探测器如何映射到算法 layer；
    4. 怎样利用 Geant4 truth 训练模型；
    5. 为什么 0.662 MeV 只能用于生成训练标签，不能作为模型输入；
    6. 如何运行训练、查看诊断结果和定位错误；
    7. 如何把训练好的模型应用到未知能源实验数据。


============================================================
第一部分：项目目标与最重要的概念
============================================================


1. 项目要解决的问题
------------------------------------------------------------

本项目面向高通量三层康普顿相机。

在真实高通量测量中，一个短符合时间窗内可能同时出现多条 gamma
产生的 hit。算法不能假定“同一行数据就是一条完整 gamma”，而应从
混合 hit 池中完成：

    1. 枚举可能的 2-hit 和 3-hit 康普顿候选；
    2. 判断候选中的 hit 是否来自同一条 gamma；
    3. 判断候选的沉积能量是否接近完整吸收；
    4. 当多个候选共享 hit 时做全局匹配；
    5. 对可信事件生成康普顿锥并加权成像。

当前版本使用可解释的线性双头模型作为基线，不是 GNN，也不是 MLEM。
当前成像方法是 weighted backprojection（加权反投影）。


2. 五个不同的数据层级
------------------------------------------------------------

必须区分以下五个概念：

    Geant4 step
        ROOT 中的一行。表示某个粒子的一次传播 step。

    detector hit
        若干 step 聚合成的像素级可观测响应。

    candidate
        算法从一个时间窗中枚举出的 2-hit 或 3-hit 假设组合。

    true gamma event
        一条真实 primary gamma 产生的全部模拟历史。

    imaging event
        不同 hit 位于不同层，并且能够生成康普顿锥的 2-hit/3-hit 事件。

数据流为：

    ROOT step
        -> detector hit
        -> fake coincidence window
        -> 2-hit / 3-hit candidate
        -> 模型概率
        -> 全局 matching
        -> 康普顿锥成像


3. Geant4 数据和实验数据的区别
------------------------------------------------------------

Geant4 模拟数据包含 truth：

    eventID
    trackID
    parentID
    stepID
    particleName
    time_ns

其中 Geant4 eventID 可以作为一条 primary gamma 的真值编号。

真实实验数据没有这种 gamma 真值。实验 EventID 可能只是硬件触发号或
时间窗编号，不能直接当成“同一条 gamma”的监督标签。

因此程序分为两条主线：

    main_geant4_train.py
        使用 Geant4 truth 训练并验证模型。

    main.py
        加载训练参数，对真实实验候选进行推理、matching 和成像。

main_geant4_train.py 内部又明确分成两条互不混淆的成像渠道：

    真值成像
        直接按 Geant4 eventID 构造同一 gamma 的跨层事件，不经过模型。

    模型成像
        从 fake coincidence window 枚举候选，由模型判断关联和全吸收概率。


============================================================
第二部分：探测器几何与 chamberID/layer 映射
============================================================


1. 三层探测器的物理顺序
------------------------------------------------------------

从源到远端的顺序为：

    源 -> ch2 -> ch1 -> ch0

其中：

    ch2：第一散射层，YSO，厚度 3 mm，最靠近源；
    ch1：第二散射层，YSO，厚度 3 mm；
    ch0：吸收层，LYSO，厚度 6 mm，最远离源。

已知底面到底面距离：

    ch2 到 ch1：25 mm
    ch1 到 ch0：35 mm

如果以 ch2 底面为相对 0，则三个底面偏移为：

    ch2： 0 mm
    ch1：25 mm
    ch0：60 mm


2. 算法 layer 定义
------------------------------------------------------------

算法 layer 按 gamma 正向传播顺序递增：

    layer 0 = ch2 = 第一 YSO
    layer 1 = ch1 = 第二 YSO
    layer 2 = ch0 = LYSO 吸收层

当前 ROOT 几何统计已经确认：

    chamberID 0：z 约 -30 mm，对应 ch2 / layer 0
    chamberID 1：z 约   0 mm，对应 ch1 / layer 1
    chamberID 2：z 约  40 mm，对应 ch0 / layer 2

因此正式映射为：

    CHAMBER_TO_LAYER = {
        0: 0,
        1: 1,
        2: 2,
    }

注意：chamberID 是 Geant4 建模编号，channel 是实验系统命名，二者不能
仅凭数字名字猜测，必须结合 z 范围、材料和厚度验证。


3. 为什么禁止使用 z 三类 k-means
------------------------------------------------------------

z_post 是 step 结束位置，不是探测器层中心。它的分布会受到：

    探测器厚度；
    材料；
    step 数量；
    粒子路径；
    边界 pre/post 坐标；
    吸收层统计量远大于散射层；

等因素影响。

强制把所有 z 值聚成三类，可能把两个薄 YSO 合并，并把厚 LYSO 拆成
两组。因此正式流程只允许使用 chamberID 或明确 layer branch。

如果二者都缺失，程序会报错停止，不会自动恢复 k-means。


4. 几何 QA
------------------------------------------------------------

Geant4RootInterface 会输出每个 chamberID 的：

    layer
    channel
    material
    step 数量
    z_min / z_max
    z 分位数和中位数

程序强制检查：

    layer 0、1、2 必须全部存在；
    z_median(layer0) < z_median(layer1) < z_median(layer2)。

如果不满足，训练立即停止。


============================================================
第三部分：ROOT 数据读取与 step-to-hit 聚合
============================================================


1. 当前 ROOT 文件结构
------------------------------------------------------------

当前使用：

    Tree: Tree1

主要 branches：

    eventID
    trackID
    stepID
    parentID
    chamberID
    pixelID
    x_pre, y_pre, z_pre
    x_post, y_post, z_post
    px_MeV, py_MeV, pz_MeV
    eDep_MeV
    kineticEnergy_MeV
    particleName
    creatorProcess
    time_ns
    Process_pre
    Process_post

其中：

    Process_post
        用于确认初级 gamma 是否实际发生了足够次数的 Compton 过程；

    parentID + particleName
        用于只统计 parentID=0 的初级 gamma，避免把次级粒子的过程误算；

    px_MeV/py_MeV/pz_MeV + time_ns + 最早位置
        只用于 Geant4 源位置和 image_plane_z 的真值几何估计，不进入模型。

如果 Process_post 不存在或其中找不到初级 gamma 的 Compton 过程，真值成像
会明确报错，而不会悄悄退化为未经物理验证的真值图。


2. eDep_MeV 与 kineticEnergy_MeV
------------------------------------------------------------

    eDep_MeV
        当前 step 在材料中的沉积能量，是 step-to-hit 能量聚合使用的字段。

    kineticEnergy_MeV
        粒子在某个 step 时刻的动能，可能是 pre-step 或 post-step 值，
        具体取决于 Geant4 输出代码。

kineticEnergy_MeV 不是沉积能量，也不能默认当作源初始能量。

当前单能 0.662 MeV 数据中，kineticEnergy_MeV 推导结果分布在
0 到 0.662 MeV，说明它主要反映相互作用后的剩余动能。


3. 为什么使用 NumPy 模式读取 ROOT
------------------------------------------------------------

程序使用：

    tree.arrays(..., library="np", how=dict)

这样可以读取 particleName 等字符串 branch，同时避免额外依赖
awkward-pandas。

服务器只需安装：

    numpy
    pandas
    matplotlib
    uproot
    awkward


4. step 过滤和 hit 聚合
------------------------------------------------------------

首先删除：

    eDep_MeV <= 0

然后按以下键聚合：

    true_event_id + layer + pixelid

聚合规则：

    energy：step 沉积能量求和；
    x/y/z：按沉积能量加权平均；
    first_time_ns：最早时间；
    first_step_id：最小 stepID；
    n_steps：被合并的 step 数量。

程序会检查聚合前后总沉积能量是否守恒。不守恒则报错停止。

当前聚合定义隐含“同一 gamma、同一层、同一像素中的 step 对实验表现为
一个 hit”。以后如果电子学能够区分同一像素中的多次相互作用，需要继续
细化这一规则。

特别注意：

    同一 EventID 内不同 pixel 的响应不会互相合并；
    一个 EventID 可以保留 2 个、3 个或更多 pixel 级 hit；
    后续从这些 pixel 级 hit 中枚举不同层的 2-hit/3-hit 组合。

因此，原始 ROOT 中 step 很多并不意味着每个 step 都是一个独立探测器
hit；但也不会再因为某个 EventID 的总 hit 数大于 3 就整条丢弃。


============================================================
第四部分：源能量、训练真值与防止信息泄漏
============================================================


1. 当前 0.662 MeV 的正确用途
------------------------------------------------------------

当前 ROOT 数据来自单能 0.662 MeV 模拟。

0.662 MeV 只允许用于：

    生成 Geant4 训练标签；
    统计真值；
    计算独立真值成像中的 oracle 康普顿角；
    验证标签和几何是否正确。

禁止用于：

    模型输入特征；
    实验推理；
    matching；
    正式未知能源成像角度。

程序中：

    FIXED_PRIMARY_ENERGY_MEV = 0.662
    PRIMARY_ENERGY_MODE = "fixed"

它们位于 main_geant4_train.py，只传给 event truth 和独立真值成像过程，
不会进入模型特征或模型成像。


2. 为什么不能从 kineticEnergy_MeV 推断 E0
------------------------------------------------------------

ROOT 很可能没有记录 primary gamma 发射时的初始 step，而是在粒子进入
敏感体或发生相互作用后才保存记录。因此即使取 primary gamma 的最大
kineticEnergy_MeV，也可能得到散射后的剩余能量。

正式 primary-energy truth 的优先来源应是：

    1. ROOT 中明确的 PrimaryEnergy branch；
    2. 每个模拟数据集配置的已知源能量；
    3. kineticEnergy 只能作为诊断，不作为正式标签来源。


3. 批量多能源训练接口
------------------------------------------------------------

未来批量训练可以在 main_geant4_train.py 中调用：

    main(
        dataset_configs=[
            {
                "dataset_id": "energy_356",
                "root_path": "/path/to/356keV.root",
                "primary_energy_mode": "fixed",
                "primary_energy_mev": 0.356,
            },
            {
                "dataset_id": "energy_662",
                "root_path": "/path/to/662keV.root",
                "primary_energy_mode": "fixed",
                "primary_energy_mev": 0.662,
            },
        ]
    )

不同 ROOT 文件中的 eventID 可能重复，程序会自动加 dataset_id 前缀。

如果未来 ROOT 增加明确 PrimaryEnergy branch，可把模式改为：

    "primary_energy_mode": "branch"


4. 模型不能看到的字段
------------------------------------------------------------

以下字段仅供 Geant4 标签和诊断使用，不能进入 scorer features：

    primary_energy
    fixed_primary_energy_mev
    true_event_id
    trackID
    parentID
    stepID truth
    abs(E_total - E0_true)

模型推理时只能使用真实实验也能获得的观测量。


============================================================
第五部分：候选事件与监督标签
============================================================


1. 正常候选顺序
------------------------------------------------------------

allow_backscatter=False 时枚举：

    layer 0 -> layer 1
    layer 0 -> layer 2
    layer 1 -> layer 2
    layer 0 -> layer 1 -> layer 2

也就是：

    ch2 -> ch1
    ch2 -> ch0
    ch1 -> ch0
    ch2 -> ch1 -> ch0


2. TwoHitEvent
------------------------------------------------------------

保存：

    hit1 / hit2
    r1 / r2
    E1 / E2
    layer、channel、pixelid
    hit 距离
    总沉积能量
    康普顿角
    模型概率和成像权重

在候选能量近似全吸收的假设下：

    E_before = E1 + E2
    E_after  = E2


3. ThreeHitEvent
------------------------------------------------------------

除了 2-hit 基础信息，还保存：

    r3、E3
    第二段距离
    第一次能量散射角
    第二次能量散射角
    第二次几何散射角
    delta_cos_second

定义：

    delta_cos_second
        = cos_theta_energy_second - cos_theta_geometry_second

对于按递增 layer 传播且末端吸收的 3-hit，delta_cos_second 应更接近 0。


4. Geant4TruthLabelBuilder
------------------------------------------------------------

该类是 Monte Carlo truth 与候选标签之间的唯一桥梁。

当前只生成两个核心监督目标：

    y_same_gamma
        candidate 中所有 hit 是否来自同一 true_event_id。

    y_full_absorption
        对 same-gamma candidate，候选自身的 E1+E2(+E3) 是否接近
        该数据集的 E0_true。

allow_backscatter=False 时，候选生成器已经强制不同 hit 位于不同层并按
layer 递增排列，因此不再使用 time_ns 或 stepID 做第二次顺序筛选。

程序也不再要求：

    candidate hit 集合 == 原 EventID 的全部可见 hit 集合

候选是否近似捕获完整能量，直接由候选能量和 E0_true 的差判断。


5. 训练前强制标签 QA
------------------------------------------------------------

程序会在训练前输出并检查：

    primary energy 来源和分布；
    y_event_full 正负样本数；
    train/validation/test same-gamma 正样本数；
    train/validation/test full-absorption 正样本数；
    三个数据子集内 2-hit/3-hit candidate 数和对应正样本数。

以下情况会直接停止：

    primary energy 缺失；
    event-full 没有正样本或没有负样本；
    same-gamma 正样本为 0；
    full-absorption 正样本为 0。

这样可以防止标签已经错误时仍继续训练并生成误导图片。


============================================================
第六部分：双头模型与训练
============================================================


1. ComptonEventScorerV2
------------------------------------------------------------

当前模型是两个 logistic head：

    match_prob
        P(candidate 中的 hit 来自同一 gamma)

    full_deposition_prob
        P(candidate 沉积能量近似完整 | candidate 来自同一 gamma)

两个不同用途的分数：

    matching_score = match_prob

    imaging_weight
        = match_prob * full_deposition_prob

matching_score 保留为可读的校准 match probability；真正决定 hit 归属的
是第七部分定义的 matching_utility。imaging_weight 决定事件对图像的贡献。

训练结束后，程序使用独立 validation 集分别校准 match_prob 和
full_deposition_prob。保存到模型文件并用于测试集及实验数据的，是校准后
的概率；未经校准的概率仍保留为事件诊断字段 match_prob_raw 和
full_deposition_prob_raw。


2. 模型特征
------------------------------------------------------------

包括：

    2-hit / 3-hit 类型；
    康普顿物理合法性；
    layer 顺序；
    是否从 layer 0 开始；
    是否终止于 layer 2 / LYSO；
    E1、E2、E3 的统计量；
    能量比例；
    能量均衡性；
    hit 距离；
    3-hit 的 delta_cos_second。

energy_feature_mode 有两种：

    "full"
        使用绝对沉积能量和比例，用于当前端到端基线。

    "normalized"
        不使用绝对总能量，只使用能量比例和几何，检查模型是否只记住
        0.662 MeV 光峰。


3. ComptonSupervisedTrainerV2
------------------------------------------------------------

损失：

    L = BCE(match_prob, y_same_gamma)
        + lambda_full * BCE(full_prob, y_full_absorption)
        + L2 regularization

full loss 只在 y_same_gamma=1 的候选上计算。

训练器支持 match/full 正样本权重，以缓解类别不平衡。

数据按 true_event_id 分成：

    70% train
    15% validation
    15% test

candidate 不能跨这三个集合，避免同一条模拟 gamma 泄漏。

当前最多训练：

    MAX_TRAINING_EPOCHS = 500

但这不是强制跑满 500 轮。程序每一轮计算 validation loss；连续
EARLY_STOPPING_PATIENCE=60 轮没有达到最小改进量时自动停止，并恢复
validation loss 最低那一轮的参数。因此是否收敛由验证集决定，不能根据
训练 loss 还在下降就盲目增加轮数。

训练完成后使用 validation 集做 Platt calibration，并在 validation 集上
选择使 same-gamma F1 最大的 matching probability threshold。test 集只做
最终评估，不参与选参数、早停、校准或阈值选择。


4. 评估指标
------------------------------------------------------------

当前入口至少输出：

    TP / FP / FN / TN
    precision
    recall
    Brier score
    validation loss 与 best epoch
    概率校准参数
    validation 自动选择的 matching threshold
    EventMatcher 前后 2-hit/3-hit 数量和分数分位数

不能只看 loss 是否下降。错误标签同样可以被拟合，loss 也会下降。

最终需要重点关注：

    match precision 是否足够；
    full-absorption 是否同时有正负样本；
    概率是否校准；
    2-hit 和 3-hit 是否分别有效。


============================================================
第七部分：全局 matching 与未知能源成像
============================================================


1. EventMatcher
------------------------------------------------------------

目标：选择一组互不共享 hit 的 candidate，使 hit-ownership utility 总和
最大。

    utility
        = n_hits
          * [logit(calibrated match_prob)
             - logit(validation threshold)]

    maximize sum(utility)
    subject to each hit used at most once

match_prob 低于 validation threshold 的 candidate 不会被选择。乘以 n_hits
的原因是：若 2-hit 和 3-hit 对相同数量的原始 hit 竞争，不能让“拆成较多
个短 candidate”仅因为概率项被重复相加而天然占便宜。该修改不会强行偏爱
3-hit；3-hit 仍需依靠自己的校准概率和无共享 hit 约束获胜。

实现：

    1. 建立共享 hit 的冲突图；
    2. 拆成 connected components；
    3. 小分量使用 branch-and-bound 精确求解；
    4. 大分量使用 greedy 近似。

matching 不使用 full probability，避免错误组合仅因能量像全吸收而赢得 hit。


2. 未知能源成像
------------------------------------------------------------

正式部署时：

    known_primary_energy_mev = None

每个 candidate 都使用自身沉积能量和估计入射能量：

    2-hit：E0_estimated = E1 + E2
    3-hit：E0_estimated = E1 + E2 + E3

full_deposition_prob 不再使用 0.5 硬门限突然删除 candidate，而是连续地
进入：

    imaging_weight = match_prob * full_deposition_prob

因此不需要预先知道真实源能量，低可信 candidate 会平滑降低图像贡献。

known_primary_energy_mev 接口只作为特殊诊断接口保留，默认关闭。


3. 成像平面
------------------------------------------------------------

main_geant4_train.py 中：

    IMAGE_PLANE_Z = None
    PLANE_DISTANCE_MM = 100.0

通用实验入口 main.py 在没有显式 z 时，会从第一散射层往源方向移动
PLANE_DISTANCE_MM 自动设置。Geant4 训练入口则会利用
primary gamma 最早 step 的位置、动量方向和 time_ns 反推发射点，并取
所有 EventID 的稳健中位数作为真实源平面 z：

    source_point ≈ step_position - c * time_ns * momentum_unit_vector

终端会输出估计的源位置、稳健离散度和样本数。如果 z 离散度大于 10 mm，
会警告人工核对 Geant4 源定义。

如果 Geant4 源平面的绝对 z 已知，应直接填写：

    IMAGE_PLANE_Z = 实际源平面 z

成像平面错误会导致正确康普顿锥也无法聚焦。


4. 真值基准图与模型图
------------------------------------------------------------

训练入口会直接调用独立模块 Geant4TruthImager.py，先生成：

    output_images/geant4_training/truth_imaging/

真值成像直接从完整 hit_df 按 true_event_id 分组。它不会再要求某个
EventID 总共“恰好只有 2 或 3 个 hit”，而是：

    1. 保留同一 EventID 的全部 pixel 级 hit；
    2. 枚举位于不同层的所有 2-hit 组合；
    3. 枚举分别位于三个不同层的所有 3-hit 组合；
    4. 2-hit 要求该初级 gamma 的 Process_post 至少记录一次 Compton；
    5. 3-hit 要求至少记录两次 Compton；
    6. 3-hit 还要求第二次散射的能量角与几何角满足
       abs(delta_cos_second) <= 0.15。

物理无效的 3-hit 不进入真值图。终端会逐项输出：原始 EventID 数、有跨层
hit 的 EventID 数、枚举出的 2-hit/3-hit 数、过程检查排除数、第二散射
排除数以及最终成像事件数。这样可以明确看出数据在哪一步减少。

它不使用 fake window、模型分数、EventMatcher 或训练/验证/测试切分。事件
权重统一为 1，并用该模拟数据集的已知 E0_true 计算第一次 oracle 散射角。
这不会把源能量泄漏到训练模型。

这张图的作用是验证：

    chamber/layer；
    r1 -> r2 方向；
    康普顿角公式；
    image_plane_z；
    坐标单位和符号。

只有真值图能够在真实源位置附近聚焦，模型图才值得解释。

模型打分结果现在固定输出两套，成像参数完全相同：

    output_images/geant4_training/model_imaging_before_match/
        EventMatcher 之前，直接使用全部 candidate 的模型成像权重。

    output_images/geant4_training/model_imaging_after_match/
        EventMatcher 之后，只使用互不共享 hit 的匹配结果。

两套目录都会生成重建图、对数图、分数直方图、权重直方图、
delta_cos_second 直方图和 top-event 单圆锥图。这样可以直接判断图像问题
是在模型打分阶段已经存在，还是由 EventMatcher 的筛选进一步引入。


5. top event 诊断图
------------------------------------------------------------

top event 不再仅按模型权重排序。

程序会计算事件康普顿锥在当前成像平面和视场中的最大响应，跳过最大响应
小于 1e-6 的事件，避免把“权重很高但锥完全不穿过视场”的事件列为 top。


============================================================
第八部分：每个 Python 文件的职责
============================================================


DataReader.py
    读取实验 ch0/ch1/ch2 数据和能量刻度文件。路径由调用方提供。

DataPreProcessor.py
    做能量刻度并构造实验宽表。如果同一 EventID 的同一 channel 有多个
    hit，会报错，避免 outer merge 产生笛卡尔组合。

Geant4RootInterface.py
    读取 ROOT、映射 chamber/layer、保留过程真值、估计源位置、过滤 step、
    按 pixel 聚合 hit 并构造 event truth。

Geant4WindowBuilder.py
    按 true_event_id 切 train/validation/test，并把多条 gamma 混成 fake
    windows。

Geant4EventSeparator.py
    从 fake windows 中枚举 2-hit/3-hit candidates。

Geant4TruthLabelBuilder.py
    为训练候选生成 y_same_gamma 和 y_full_absorption 两个监督标签。

Geant4TruthImager.py
    独立真值成像模块。直接按 true_event_id 枚举跨层 2-hit/3-hit，
    使用 Process_post 和第二散射一致性排除无效 3-hit，不使用 fake window、
    训练模型、matching 或数据集切分。

EventSeparator.py
    从真实实验宽表中构造候选，不使用 Geant4 truth。

TwoHitEvent.py
    保存单个 2-hit candidate 的可观测物理量和模型输出。

ThreeHitEvent.py
    保存单个 3-hit candidate，包括第二次散射几何一致性。

EventList.py
    保存候选对象，支持 DataFrame、筛选和排序。

ComptonEventScorerV2.py
    双头线性概率模型，输出 match/full 和两个用途不同的权重。

ComptonSupervisedTrainerV2.py
    使用 Geant4 标签训练双头模型，并根据 validation loss 早停和恢复最佳
    参数。

ProbabilityCalibrator.py
    在 validation 集上分别对 match/full raw logits 做 Platt calibration。

EventMatcher.py
    使用校准概率、validation 阈值和 hit 数量归一化 utility，在共享 hit
    约束下做全局候选匹配。

ComptonConeImager.py
    生成康普顿锥响应、加权反投影和诊断图。

main_geant4_train.py
    Geant4 训练、测试、truth QA、真值成像、模型成像和参数保存入口。

main.py
    真实实验推理入口。加载训练参数，不重新监督训练。

ComptonEventScorer.py
ComptonLossLandscape.py
ComptonGradientTrainer.py
ComptonTrainTestSplitter.py
    旧版单头训练和早期调试代码，仅保留用于历史参考。


============================================================
第九部分：如何运行
============================================================


1. Python 环境
------------------------------------------------------------

推荐 Python 3.8 以上。

安装依赖：

    pip install numpy pandas matplotlib uproot awkward

不要求安装 awkward-pandas。


2. 设置 ROOT 路径
------------------------------------------------------------

main_geant4_train.py 默认：

    DEFAULT_ROOT_PATH = PROGRAM_DIR.parent / "20260714_lyso.root"

服务器可改为：

    DEFAULT_ROOT_PATH = Path(
        "/home/用户名/项目目录/20260714_lyso.root"
    )


3. 运行 Geant4 训练
------------------------------------------------------------

在程序目录运行：

    python main_geant4_train.py

运行顺序：

    ROOT 读取
    -> 几何 QA
    -> 初级 gamma 发射位置/真实源平面估计
    -> truth QA
    -> 独立 Geant4 过程验证与真值成像
    -> train/validation/test 切分
    -> candidate 标签 QA
    -> 双头训练、validation loss 和早停
    -> validation 概率校准与 matching threshold 选择
    -> 校准后的 test 指标
    -> EventMatcher 前 2-hit/3-hit 数量和分数
    -> 使用所有已打分 candidate 生成 match 前全部诊断图
    -> matching
    -> EventMatcher 后 2-hit/3-hit 数量和分数
    -> 使用匹配结果生成 match 后全部诊断图


4. 输出位置
------------------------------------------------------------

模型参数：

    程序目录/compton_scorer_v2_params.json

真值基准图片：

    程序目录/output_images/geant4_training/truth_imaging/

模型图片（匹配前）：

    程序目录/output_images/geant4_training/model_imaging_before_match/

模型图片（匹配后）：

    程序目录/output_images/geant4_training/model_imaging_after_match/

实验图片：

    程序目录/output_images/experiment/before_match/
    程序目录/output_images/experiment/after_match/


5. 运行实验推理
------------------------------------------------------------

先在 main.py 的 EXPERIMENT_PATHS 中填写：

    ch0_path
    ch1_path
    ch2_path
    calibration_ch0_path
    calibration_ch1_path
    calibration_ch2_path

然后运行：

    python main.py

实验入口会加载 compton_scorer_v2_params.json，不会使用实验 truth，也不会
重新训练模型。


============================================================
第十部分：正确的调试顺序
============================================================


第一步：检查 geometry QA

    chamber 0 -> layer 0 -> ch2 -> z 约 -30 mm
    chamber 1 -> layer 1 -> ch1 -> z 约   0 mm
    chamber 2 -> layer 2 -> ch0 -> z 约  40 mm

第二步：检查 primary energy QA

当前单能数据应全部为：

    primary_energy = 0.662 MeV
    source = fixed_dataset_truth

如果分布在 0 到 0.662 MeV，说明错误使用了 kineticEnergy_MeV。

第三步：检查标签数量

    event-full 必须有正负样本；
    same-gamma 必须有正样本；
    full-absorption 必须有正样本。

第四步：检查 truth_imaging 图

如果真值图不能在真实源附近聚焦，优先检查：

    自动估计的 source position 和 z robust spread；
    IMAGE_PLANE_Z 人工覆盖值；
    源位于正 z 还是负 z；
    r1 -> r2 方向；
    康普顿公式；
    坐标和单位。

第五步：检查模型指标

先检查 best validation loss 和 best epoch，再检查校准后的 test precision、
recall 与 Brier score，不能只看 train loss。

同时对照：

    before EventMatcher 3-hit count / match_prob 分位数；
    after EventMatcher 3-hit count / match_prob 分位数。

如果匹配前已有 3-hit、匹配后为 0，问题在 matching 竞争或阈值；如果匹配
前就是 0，问题在 candidate 枚举或更早的物理构造，不能归因于 EventMatcher。

第六步：对比 model_imaging_before_match 与 model_imaging_after_match

只有 truth 图正确、模型指标合理后，才能讨论模型成像效果。


============================================================
第十一部分：当前限制与后续工作
============================================================


1. 当前只有 0.662 MeV 单能源数据，只能验证流程，不能证明对未知能源泛化。

2. 绝对能量特征可能让模型学习 0.662 MeV 光峰捷径。应比较 full 与
   normalized 两种 energy_feature_mode。

3. 2-hit 的未知能源全吸收判断存在物理歧义，输出应理解为概率，而不是
   确定性结论。

4. 当前暂不考虑 back scattering，候选顺序完全由递增 layer 定义。未来
   若加入 back scattering，必须另外设计可观测排序模型和 Geant4 监督标签。

5. 当前实验预处理仍是每通道每 EventID 至多一个 hit 的宽表模式。正式
   高通量实验应升级为长表 coincidence-window hit pool。

6. 当前 scorer 是线性模型。当前版本已经加入 validation 概率校准，但单能
   数据的 calibration 仍不能证明跨能源有效。积累多能源数据后可升级为
   小型 MLP 或 layer-aware GNN。

7. 当前成像是加权反投影。真值几何正确后，才考虑 weighted list-mode
   MLEM，不能用 MLEM 掩盖错误事件或错误锥。


============================================================
第十二部分：必须长期遵守的原则
============================================================


1. 几何先于模型。

2. ROOT step 不等于 detector hit。

3. 真值成像与模型成像必须完全分开，不能让模型候选筛选污染真值基准。

4. kineticEnergy_MeV 不等于 eDep_MeV，也不默认等于源初始能量。

5. 数据集源能量可以用于生成训练标签，但不能进入模型输入。

6. train/validation/test 必须按 true_event_id 切分，禁止按 candidate
   随机切分。

7. truth_imaging 基准图不正确时，禁止解释 match 前后的模型成像图。

8. train loss 下降不等于物理正确，必须同时检查 validation loss、标签、
   precision、校准和图像。

9. 每次运行保留 geometry、truth、label、loss、test metrics 和图像记录。

10. 修改正式逻辑后应从 ROOT 重新生成 hit、candidate 和标签，并重新训练，
    不能继续使用旧模型参数。
