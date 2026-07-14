README.txt
============================================================
三层康普顿相机事件构建、Geant4监督训练与康普顿锥成像程序说明
============================================================

本程序目前分成两条主线：

1. Geant4 模拟数据训练线
   使用 .root 文件中的 Geant4 truth 信息训练事件打分器。
   入口建议命名为：
       main_geant4_train.py

2. 真实实验数据应用线
   读取真实实验数据，用 Geant4 训练好的参数对候选事件打分、matching、成像。
   入口建议命名为：
       main.py

二者核心区别：

    Geant4 模拟数据有 true_event_id，可以知道哪些 hit 来自同一个 gamma。
    真实实验数据没有 true_event_id，需要模型根据打分和 matching 判断哪些 hit 属于同一个 gamma。


============================================================
第一部分：程序结构、每个 .py / 类的职责、输入输出接口和原理
============================================================


1. DataReader.py
------------------------------------------------------------

职责：
    读取真实实验数据的原始文件，例如 ch0、ch1、ch2 三层探测器的 txt/csv 数据。

典型输入：
    原始实验数据文件，通常每层一个文件。

典型输出：
    DataReader 对象内部保存每个通道的数据表。

常见字段：
    EventID
    TotalEnergy
    PixelID
    pos_x_mm
    pos_y_mm
    z

注意：
    在真实实验数据中，EventID 不一定代表同一个 gamma 的真实物理事件。
    它可能只是电子学或数据采集层面的触发/时间编号。
    因此真实实验中不能用 EventID 当作监督标签。


2. DataPreProcessor.py
------------------------------------------------------------

职责：
    对 DataReader 读入的真实实验数据做预处理，并把 ch0/ch1/ch2 合并成 final_df。

主要功能：
    1. 能量校准；
    2. 坐标整理；
    3. 按 EventID 合并三层 hit；
    4. 输出宽表 final_df。

典型输入：
    DataReader 对象。

典型输出：
    final_df，形如：

        EventID
        ch0_pixelid, ch0_x, ch0_y, ch0_z, ch0_energy
        ch1_pixelid, ch1_x, ch1_y, ch1_z, ch1_energy
        ch2_pixelid, ch2_x, ch2_y, ch2_z, ch2_energy

后续对接：
    final_df 会输入到 EventSeparator，用于构造 TwoHitEvent / ThreeHitEvent。

注意：
    这个模块主要服务于真实实验数据。
    对 Geant4 .root 数据，不建议走 DataReader + DataPreProcessor，
    而是走 Geant4RootInterface。


3. ComptonTrainTestSplitter.py
------------------------------------------------------------

类名：
    ComptonTrainTestSplitter

职责：
    把 DataPreProcessor 输出的 final_df 按 EventID 分成 train_df 和 test_df。

典型输入：
    final_df

典型输出：
    train_df
    test_df

主要参数：
    train_ratio:
        训练集比例，默认 0.8。
    random_seed:
        随机种子，保证可复现。
    event_id_column:
        EventID 列名，默认 "EventID"。
    shuffle:
        是否打乱 EventID 后再划分。

原理：
    按 EventID 切分，而不是按 DataFrame 行切分。
    这样可以避免同一个 EventID 的数据同时进入训练集和测试集。

当前定位：
    这个类对早期实验数据调试有用。
    对正式 Geant4 监督训练，更推荐使用 Geant4WindowBuilder 里的 split_train_test，
    因为 Geant4 训练需要按 true_event_id 切分。


4. TwoHitEvent.py
------------------------------------------------------------

类名：
    TwoHitEvent

职责：
    表示一个 2-hit 候选康普顿事件。

一个 TwoHitEvent 对象只表示一个候选事件，例如：

    h1 -> h2

内部保存的信息：
    event_id
    hit1, hit2
    hit_ids
    channels
    layers
    pixelids
    r1, r2
    E1, E2
    E_total
    distance_12
    cos_theta_c
    theta_c
    is_physical

Geant4 truth 信息：
    true_event_ids
    primary_energies
    y_match
    y_full
    y_usable

模型输出信息：
    score
    match_prob
    full_deposition_prob
    imaging_weight

输入接口：
    TwoHitEvent(event_id, hit1, hit2)

其中 hit1/hit2 是 dict，至少包含：

    hit_id
    layer
    channel
    pixelid
    pos
    energy

若来自 Geant4，还应包含：

    true_event_id
    primary_energy

核心物理计算：
    当前 TwoHitEvent 会计算：

        E_total = E1 + E2

    并在“全能量沉积假设”下计算康普顿角：

        E_before = E1 + E2
        E_after  = E2

    注意：
        这个角度只有在 full_deposition_prob 较高时才应该用于成像。
        对逃逸事件，E1 + E2 不等于入射 gamma 总能量，不能直接用这个角度。

监督标签：
    y_match:
        如果 hit1.true_event_id == hit2.true_event_id，则 y_match = 1；
        否则 y_match = 0。

    y_full:
        只对 y_match=1 的候选有意义。
        若 abs(E_total - primary_energy) < tolerance，则 y_full = 1；
        否则 y_full = 0。

    y_usable:
        当前第一版定义为 y_match=1 且 y_full=1。


5. ThreeHitEvent.py
------------------------------------------------------------

类名：
    ThreeHitEvent

职责：
    表示一个 3-hit 候选康普顿事件。

一个 ThreeHitEvent 对象只表示一个候选事件，例如：

    h1 -> h2 -> h3

内部保存的信息：
    event_id
    hit1, hit2, hit3
    hit_ids
    channels
    layers
    pixelids
    r1, r2, r3
    E1, E2, E3
    E_total
    distance_12
    distance_23
    cos_theta_c_first
    theta_c_first
    cos_theta_c_second
    cos_theta_g_second
    delta_cos_second
    is_physical

Geant4 truth 信息：
    true_event_ids
    primary_energies
    y_match
    y_full
    y_usable

模型输出信息：
    score
    match_prob
    full_deposition_prob
    imaging_weight

输入接口：
    ThreeHitEvent(event_id, hit1, hit2, hit3, sigma_delta_cos=0.15)

核心物理计算：
    第一次散射角，当前按全能量沉积假设：

        E_before = E1 + E2 + E3
        E_after  = E2 + E3

    第二次散射角，当前按全能量沉积假设：

        E_before = E2 + E3
        E_after  = E3

    第二次几何散射角：

        入射方向 = r2 - r1
        出射方向 = r3 - r2

    3-hit 的重要自洽量：

        delta_cos_second = cos_theta_c_second - cos_theta_g_second

    如果一个 3-hit 候选是真实且全沉积的，delta_cos_second 应该更接近 0。

注意：
    delta_cos_second 对逃逸事件可能不可靠，因为它使用了全沉积假设。
    因此后续用 full_deposition_prob gate 控制是否让该事件参与成像。

监督标签：
    y_match:
        三个 hit 的 true_event_id 全相同，则 y_match=1；
        否则 y_match=0。

    y_full:
        对 y_match=1 的事件，若 E_total 接近 primary_energy，则 y_full=1；
        否则 y_full=0。


6. EventList.py
------------------------------------------------------------

类名：
    EventList

职责：
    保存所有 TwoHitEvent 和 ThreeHitEvent 对象。

内部结构：
    self.events:
        事件对象列表。

    self.indexes:
        事件索引列表。

主要方法：
    add_event(event):
        添加一个 TwoHitEvent 或 ThreeHitEvent。

    get_event(index):
        根据索引获取事件对象。

    get_indexes():
        获取所有索引。

    to_dataframe():
        把所有 event.to_dict() 合并成 pandas DataFrame，方便检查和画图。

    sort_by_score(descending=True):
        按 event.score 排序并返回索引。

    get_two_hit_events():
        返回所有 TwoHitEvent。

    get_three_hit_events():
        返回所有 ThreeHitEvent。

输入输出：
    输入：一个个 event 对象。
    输出：EventList 对象本身，或 DataFrame。


7. EventSeparator.py
------------------------------------------------------------

类名：
    EventSeparator

职责：
    从真实实验数据的 final_df 中划分 2-hit / 3-hit 候选事件。

输入：
    final_df

输出：
    EventList

工作流程：
    1. 遍历 final_df 每一行；
    2. 从 ch0/ch1/ch2 提取有效 hit；
    3. 枚举 2-hit 候选；
    4. 枚举 3-hit 候选；
    5. 每个候选包装成 TwoHitEvent / ThreeHitEvent；
    6. 存入 EventList。

主要参数：
    min_energy:
        hit 能量阈值，低于该值的 hit 不参与候选构建。

    allow_backscatter:
        是否枚举反向/乱序候选。
        第一版建议 False。

    sigma_delta_cos:
        3-hit 自洽性相关参数，传给 ThreeHitEvent。

注意：
    EventSeparator 是给真实实验 final_df 用的。
    它不利用 Geant4 truth。
    Geant4 .root 训练不要用它，而用 Geant4EventSeparator。


8. Geant4RootInterface.py
------------------------------------------------------------

类名：
    Geant4RootInterface

职责：
    专门读取 Geant4 .root 文件，并转换成统一格式的 hit_df。

输入：
    root_path:
        .root 文件路径。

    tree_name:
        ROOT 中的 TTree 名字。可设 None 自动寻找。

    branch_map:
        ROOT branch 名字映射。若自动识别失败，需要手动指定。

    energy_unit:
        能量单位，默认 MeV。

    position_unit:
        位置单位，默认 mm。

输出：
    hit_df，标准列为：

        true_event_id
        hit_id
        layer
        channel
        pixelid
        x
        y
        z
        energy
        primary_energy

核心意义：
    true_event_id 是 Geant4 中同一个 gamma 的真实事件编号。
    这是训练 y_match 的核心监督信息。

自动识别 branch：
    程序会尝试自动寻找类似下面的 branch：

        EventID / eventID / event_id / gammaID
        TotalEnergy / edep / Edep / energy
        pos_x_mm / x / posX
        pos_y_mm / y / posY
        z / pos_z_mm / posZ
        layer / channel / detectorID
        PixelID / copyNo
        PrimaryEnergy / E0 / gammaEnergy

如果自动识别失败：
    程序会打印当前 ROOT 文件中的所有 branch。
    然后需要在 main_geant4_train.py 中手动填写 branch_map。

示例：

    interface = Geant4RootInterface(
        root_path="data/20260714_lyso.root",
        tree_name="Hits",
        branch_map={
            "EventID": "eventID",
            "TotalEnergy": "edep",
            "pos_x_mm": "x",
            "pos_y_mm": "y",
            "z": "z",
            "layer": "layerID",
            "PixelID": "pixelID",
            "PrimaryEnergy": "primaryEnergy",
        },
    )


9. Geant4WindowBuilder.py
------------------------------------------------------------

类名：
    Geant4WindowBuilder

职责：
    把 Geant4 hit_df 按 true_event_id 混合成训练用 fake coincidence windows。

输入：
    hit_df

输出：
    windows，一个 list。
    每个 window 是 dict：

        {
            "window_id": int,
            "true_event_ids": list,
            "hit_df": DataFrame
        }

主要参数：
    event_ids_per_window:
        每个 fake window 中混合多少个 Geant4 true_event_id。
        值越大，负样本越多，训练更接近高通量真实实验。
        但候选数量也会快速增加。

    random_seed:
        随机种子。

    shuffle:
        是否打乱 true_event_id。

主要方法：
    split_train_test(train_ratio=0.8):
        按 true_event_id 切分 train_hit_df / test_hit_df。
        这样避免同一个 gamma 同时出现在训练集和测试集。

    build_windows():
        把多个 true_event_id 混在一个 window 中。

原理：
    真实实验中一个时间窗内可能有多个 gamma 的 hit。
    Geant4 每个 EventID 本来是干净单 gamma。
    因此需要人为混合多个 true_event_id，制造真实实验中的 hit association 难题。

标签来源：
    window 中枚举出的候选：

        hit 全来自同一个 true_event_id  -> y_match = 1
        hit 来自不同 true_event_id      -> y_match = 0


10. Geant4EventSeparator.py
------------------------------------------------------------

类名：
    Geant4EventSeparator

职责：
    从 Geant4 fake coincidence windows 中枚举 2-hit / 3-hit candidates。

输入：
    windows，由 Geant4WindowBuilder.build_windows() 生成。

输出：
    EventList

工作流程：
    1. 遍历每个 window；
    2. 从 window["hit_df"] 中提取 hit；
    3. 枚举 2-hit candidates；
    4. 枚举 3-hit candidates；
    5. 包装成 TwoHitEvent / ThreeHitEvent；
    6. 事件对象内部自动生成 y_match / y_full / y_usable。

主要参数：
    min_energy:
        hit 能量阈值。

    allow_backscatter:
        是否枚举反向/乱序候选。
        第一版建议 False。

    sigma_delta_cos:
        传给 ThreeHitEvent。

    max_candidates_per_window:
        限制每个 window 最多生成多少候选。
        数据很大时可用于防止候选爆炸。

与 EventSeparator 的区别：
    EventSeparator:
        输入真实实验 final_df。
        没有 truth label。

    Geant4EventSeparator:
        输入 Geant4 fake windows。
        hit 中带 true_event_id。
        可以自动生成监督标签。


11. ComptonEventScorer.py
------------------------------------------------------------

类名：
    ComptonEventScorer

职责：
    旧版单头打分器。

输出：
    event.score

原理：
    score = sigmoid(linear(features))

局限：
    它只有一个 score。
    无法区分：
        hit 是否匹配正确；
        gamma 是否全能量沉积；
        event 是否可用于成像。

当前建议：
    保留用于历史参考。
    新训练与新成像建议使用 ComptonEventScorerV2。


12. ComptonEventScorerV2.py
------------------------------------------------------------

类名：
    ComptonEventScorerV2

职责：
    新版双头打分器，包含 full-deposition gate。

输入：
    EventList

输出：
    直接修改 EventList 内每个 event 对象：

        event.match_prob
        event.full_deposition_prob
        event.imaging_weight
        event.score

核心输出：
    match_prob:
        P(candidate hit 属于同一条 gamma 且组合正确)

    full_deposition_prob:
        P(candidate 对应 gamma 在探测器中全能量沉积)

    imaging_weight:
        用于成像的最终权重：

        imaging_weight = match_prob * full_deposition_prob

    score:
        为了兼容 EventMatcher，当前设置为 imaging_weight。

主要参数：
    match_params:
        match head 的可学习参数。

    full_params:
        full-deposition head 的可学习参数。

    energy_scale_mev:
        能量归一化尺度。

    distance_scale_mm:
        距离归一化尺度。

特征：
    bias
    is_two_hit
    is_three_hit
    is_physical
    layer_order_score
    E_total_norm
    E_mean_norm
    E_max_norm
    energy_balance
    distance_12_norm
    distance_23_norm
    abs_delta_cos_second
    delta_cos_second_squared
    ends_in_last_layer

原理：
    以前代码默认：

        E_in = E1 + E2 (+ E3)

    这隐含全沉积假设，对 escape event 会错。

    新版逻辑：
        先学习 full_deposition_prob。
        只有 full_deposition_prob 高的 event，才允许强烈参与成像。
        因此沉积能量和推算入射能量这一步受 gate 控制。


13. ComptonSupervisedTrainerV2.py
------------------------------------------------------------

类名：
    ComptonSupervisedTrainerV2

职责：
    使用 Geant4 truth 训练 ComptonEventScorerV2。

输入：
    ComptonEventScorerV2 对象。

输出：
    更新 scorer.match_params 和 scorer.full_params。

训练标签来源：
    event.y_match
    event.y_full

损失函数：
    L = BCE(match_prob, y_match)
        + lambda_full * y_match * BCE(full_deposition_prob, y_full)
        + L2 regularization

重要细节：
    full_deposition_prob 只对 y_match=1 的候选有明确意义。
    因此 full loss 前面乘了 y_match。
    错误组合不会污染 full-deposition gate。

主要参数：
    learning_rate:
        学习率。

    lambda_full:
        full-deposition loss 权重。

    lambda_reg:
        L2 正则项权重。

    epochs:
        训练轮数。


14. EventMatcher.py
------------------------------------------------------------

类名：
    EventMatcher

职责：
    从 EventList 中选择一组互不共享 hit 的 event，并使总分最大。

输入：
    EventList

输出：
    修改后的 EventList，只保留被选中的 event。

约束：
    同一个 hit 不能被多个 event 重复使用。

优化目标：
    maximize sum(event.score)

原理：
    这是 weighted set packing / hypergraph matching 问题。
    如果只用贪心，可能局部最优但全局不优。

实现：
    1. 根据共享 hit 关系建立 conflict graph；
    2. 把 event 分成若干 connected components；
    3. 对小 component 使用 branch and bound 精确搜索；
    4. 对大 component 使用 greedy 近似；
    5. 重写 EventList，只保留 selected events。

主要参数：
    max_exact_events:
        每个 conflict component 允许精确搜索的最大 event 数量。
        默认可设 28 左右。
        值越大越精确，但越慢。

注意：
    EventMatcher 使用 event.score。
    在 V2 里 event.score = event.imaging_weight。
    因此 matching 同时考虑了匹配正确概率和全沉积概率。


15. ComptonConeImager.py
------------------------------------------------------------

类名：
    ComptonConeImager

职责：
    把 EventList 中的 event 转成康普顿锥响应，并在探测器前方某个平面上成像。

输入：
    EventList

输出：
    图像矩阵 self.image
    诊断图像文件

核心流程：
    1. 根据 event.imaging_weight 计算成像权重；
    2. 对每个 event 读取 r1、r2 和康普顿角；
    3. 在指定 z 平面生成 x-y 网格；
    4. 对每个像素计算该像素是否落在康普顿锥上；
    5. 把所有 event response 加权叠加。

成像权重：
    V2 推荐：

        weight = event.imaging_weight
               = event.match_prob * event.full_deposition_prob

康普顿角 gate：
    当前建议：
        如果 event.full_deposition_prob < 0.5，
        则不使用 deposited-energy-sum 推出的康普顿角。

原因：
    deposited-energy-sum 推角度隐含全沉积假设。
    逃逸事件不能直接用这个角度成像。

主要参数：
    image_plane_z:
        成像平面 z 坐标。
        若为 None，则自动从探测器前层往前推 plane_distance_mm。
        对已知源平面，建议手动设置。

    plane_distance_mm:
        自动成像平面距离探测器前层多远。
        默认 100 mm。

    x_range, y_range:
        成像区域范围，例如 (-150, 150)。

    n_pixels:
        图像像素数。

    sigma_angle_deg:
        单个 cone response 的角度宽度。
        越小环越细，但对误差更敏感。

    min_score:
        最小成像权重阈值。

    output_dir:
        诊断图保存目录。

输出诊断图：
    01_reconstructed_image.png
    02_log_reconstructed_image.png
    03_event_score_histogram.png
    04_event_weight_histogram.png
    05_delta_cos_second_histogram.png
    06_top_event_response_*.png


============================================================
第二部分：怎么使用、参数怎么调、路径怎么放、main 如何设计
============================================================


1. 推荐目录结构
------------------------------------------------------------

建议工程目录如下：

    FirstArithmetic2.0/
        DataReader.py
        DataPreProcessor.py
        ComptonTrainTestSplitter.py

        TwoHitEvent.py
        ThreeHitEvent.py
        EventList.py

        EventSeparator.py
        Geant4RootInterface.py
        Geant4WindowBuilder.py
        Geant4EventSeparator.py

        ComptonEventScorer.py
        ComptonEventScorerV2.py
        ComptonSupervisedTrainerV2.py
        ComptonLossLandscape.py
        ComptonGradientTrainer.py

        EventMatcher.py
        ComptonConeImager.py

        main.py
        main_geant4_train.py
        README.txt

        data/
            20260714_lyso.root
            experimental_ch0.txt
            experimental_ch1.txt
            experimental_ch2.txt

        figure/
            geant4_v2_imaging/
            experiment_imaging/

        compton_scorer_v2_params.json


2. 依赖环境
------------------------------------------------------------

基础依赖：
    numpy
    pandas
    matplotlib

读取 ROOT 需要：
    uproot
    awkward

安装命令：

    pip install numpy pandas matplotlib uproot awkward

Python 版本：
    你当前环境是 Python 3.8。
    因此代码里不要使用 Python 3.9+ 才支持的字典合并语法：

        dict_a | dict_b

    应使用：

        dict_a.update(dict_b)

推荐：
    若条件允许，建议使用 Python 3.10 或 3.11。
    但当前代码应尽量保持 Python 3.8 兼容。


3. Geant4 .root 文件怎么放
------------------------------------------------------------

把 Geant4 ROOT 文件放到：

    data/20260714_lyso.root

然后在 main_geant4_train.py 中设置：

    root_path = "data/20260714_lyso.root"

如果使用绝对路径：

    root_path = "/home/ezqi/labwork/SourceRecon/FirstArithmetic2.0/data/20260714_lyso.root"

注意：
    不要使用 ChatGPT 沙盒路径：

        /mnt/data/20260714_lyso.root

    这个路径只在 ChatGPT 的运行环境中存在，
    不一定存在于你的远程服务器。


4. 先跑哪个 main
------------------------------------------------------------

处理 Geant4 .root 模拟数据时：

    python main_geant4_train.py

处理真实实验数据时：

    python main.py

推荐顺序：

    第一步：
        跑 main_geant4_train.py
        用 Geant4 truth 训练打分器。

    第二步：
        保存 compton_scorer_v2_params.json。

    第三步：
        跑 main.py
        加载训练好的参数，应用到真实实验数据。


5. main_geant4_train.py 设计原则
------------------------------------------------------------

main_geant4_train.py 只做训练，不处理真实实验数据。

推荐流程：

    1. Geant4RootInterface 读取 .root，输出 hit_df。
    2. Geant4WindowBuilder 按 true_event_id 划分 train/test。
    3. Geant4WindowBuilder 构造 fake coincidence windows。
    4. Geant4EventSeparator 枚举候选 event。
    5. ComptonEventScorerV2 初始化双头 scorer。
    6. ComptonSupervisedTrainerV2 用 y_match 和 y_full 训练。
    7. 保存 compton_scorer_v2_params.json。
    8. 在 test set 上 EventMatcher。
    9. 用 ComptonConeImager 输出诊断图。

关键代码结构：

    root_path = "data/20260714_lyso.root"

    interface = Geant4RootInterface(
        root_path=root_path,
        tree_name=None,
        branch_map=None,
    )

    hit_df = interface.load()
    interface.print_summary()

    splitter = Geant4WindowBuilder(
        hit_df=hit_df,
        event_ids_per_window=5,
        random_seed=42,
    )

    train_hit_df, test_hit_df = splitter.split_train_test(train_ratio=0.8)

    train_window_builder = Geant4WindowBuilder(
        hit_df=train_hit_df,
        event_ids_per_window=5,
        random_seed=1,
    )
    train_windows = train_window_builder.build_windows()

    test_window_builder = Geant4WindowBuilder(
        hit_df=test_hit_df,
        event_ids_per_window=5,
        random_seed=2,
    )
    test_windows = test_window_builder.build_windows()

    train_separator = Geant4EventSeparator(
        windows=train_windows,
        min_energy=0.0,
        allow_backscatter=False,
        sigma_delta_cos=0.15,
        max_candidates_per_window=None,
    )
    train_event_list = train_separator.separate()

    test_separator = Geant4EventSeparator(
        windows=test_windows,
        min_energy=0.0,
        allow_backscatter=False,
        sigma_delta_cos=0.15,
        max_candidates_per_window=None,
    )
    test_event_list = test_separator.separate()

    train_scorer = ComptonEventScorerV2(train_event_list)
    train_scorer.score_all_events()

    trainer = ComptonSupervisedTrainerV2(
        scorer=train_scorer,
        learning_rate=0.05,
        lambda_full=1.0,
        lambda_reg=1e-4,
    )

    trainer.fit(
        epochs=100,
        verbose=True,
    )

    with open("compton_scorer_v2_params.json", "w") as f:
        json.dump(
            {
                "match_params": train_scorer.match_params,
                "full_params": train_scorer.full_params,
            },
            f,
            indent=4,
        )


6. main.py 设计原则
------------------------------------------------------------

main.py 只处理真实实验数据，不重新训练。

推荐流程：

    1. DataReader 读取实验数据。
    2. DataPreProcessor 输出 final_df。
    3. EventSeparator 枚举候选 event。
    4. 读取 compton_scorer_v2_params.json。
    5. ComptonEventScorerV2 对真实实验 event 打分。
    6. EventMatcher 选择互不冲突事件。
    7. ComptonConeImager 成像。

关键代码结构：

    reader = DataReader()
    reader.read_data()

    preprocessor = DataPreProcessor(reader)
    final_df = preprocessor.build_final_df()

    separator = EventSeparator(
        final_df=final_df,
        min_energy=0.0,
        allow_backscatter=False,
        sigma_delta_cos=0.15,
    )
    event_list = separator.separate()

    with open("compton_scorer_v2_params.json", "r") as f:
        params = json.load(f)

    scorer = ComptonEventScorerV2(
        event_list=event_list,
        match_params=params["match_params"],
        full_params=params["full_params"],
    )
    scorer.score_all_events()

    matcher = EventMatcher(event_list)
    matched_event_list = matcher.match()

    imager = ComptonConeImager(
        event_list=matched_event_list,
        image_plane_z=None,
        plane_distance_mm=100.0,
        x_range=(-150.0, 150.0),
        y_range=(-150.0, 150.0),
        n_pixels=200,
        sigma_angle_deg=5.0,
        min_score=0.05,
        output_dir="figure/experiment_imaging",
    )

    paths = imager.save_all_diagnostic_plots()


7. ROOT branch_map 怎么设置
------------------------------------------------------------

如果运行 main_geant4_train.py 时报错：

    KeyError: 找不到 branch

先看程序打印的：

    [Geant4RootInterface] branches:

然后根据实际 branch 名手动填写 branch_map。

示例：

    interface = Geant4RootInterface(
        root_path=root_path,
        tree_name="Hits",
        branch_map={
            "EventID": "EventID",
            "TotalEnergy": "TotalEnergy",
            "pos_x_mm": "pos_x_mm",
            "pos_y_mm": "pos_y_mm",
            "z": "z",
            "layer": "layer",
            "PixelID": "PixelID",
            "PrimaryEnergy": "PrimaryEnergy",
        },
    )

左边 key 是程序内部标准名，不建议改。
右边 value 是 ROOT 文件中的真实 branch 名。


8. 重要可调参数
------------------------------------------------------------

event_ids_per_window:
    位置：Geant4WindowBuilder
    含义：每个 fake coincidence window 混合多少个 Geant4 true_event_id。
    默认建议：5。
    越大负样本越多，但候选数量增长很快。
    调试时可用 2 或 3，正式训练可用 5 或 10。

train_ratio:
    位置：split_train_test(train_ratio=0.8)
    含义：训练集比例。
    默认建议：0.8。
    必须按 true_event_id 切分，不能按 candidate 随机切分。

min_energy:
    位置：EventSeparator / Geant4EventSeparator
    含义：hit 能量阈值。
    默认：0.0。
    若低能噪声较多，可设 0.01 MeV 或 0.02 MeV。

allow_backscatter:
    位置：EventSeparator / Geant4EventSeparator
    含义：是否枚举反向/乱序 hit 顺序。
    默认建议：False。
    若要研究 backscatter，可以设 True，但候选数量会明显增加。

sigma_delta_cos:
    位置：ThreeHitEvent / EventSeparator / Geant4EventSeparator
    含义：3-hit 内部康普顿一致性相关宽度。
    默认：0.15。
    在 V2 中它主要是辅助特征，不建议只靠这个手写规则判断好坏。

learning_rate:
    位置：ComptonSupervisedTrainerV2
    默认：0.05。
    若 loss 不稳定，可降到 0.01。
    若下降太慢，可试 0.1。

lambda_full:
    位置：ComptonSupervisedTrainerV2
    含义：full-deposition gate 的 loss 权重。
    默认：1.0。
    若逃逸事件仍然污染图像，可提高到 2.0。

lambda_reg:
    位置：ComptonSupervisedTrainerV2
    含义：L2 正则强度。
    默认：1e-4。

max_candidates_per_window:
    位置：Geant4EventSeparator
    默认：None。
    用于限制每个 window 最多生成多少候选，防止候选爆炸。
    调试阶段可设 1000 或 5000。

max_exact_events:
    位置：EventMatcher
    含义：conflict component 中最多多少个 event 使用精确 branch-and-bound。
    默认建议：28。
    越大越接近全局最优，但越慢。

image_plane_z:
    位置：ComptonConeImager
    含义：成像平面 z 坐标。
    默认 None，程序自动估计。
    如果源平面已知，强烈建议手动设置。
    z 平面设错会导致图像变糊。

plane_distance_mm:
    位置：ComptonConeImager
    含义：当 image_plane_z=None 时，自动把成像平面放在探测器前方多远。
    默认：100.0。

x_range / y_range:
    位置：ComptonConeImager
    含义：成像区域范围。
    默认：(-150.0, 150.0)。
    视场更大时可改成 (-300.0, 300.0)。

n_pixels:
    位置：ComptonConeImager
    含义：图像分辨率。
    默认：200。
    越大图像越细，但计算越慢。

sigma_angle_deg:
    位置：ComptonConeImager
    含义：每个 cone response 的角度宽度。
    默认：5.0 度。
    越小环越细，图像可能更锐，但对误差更敏感。

min_score:
    位置：ComptonConeImager
    含义：最小成像权重阈值。
    默认建议：0.05。
    提高 min_score 可以减少低质量事件污染，但会降低统计量。


9. 输出文件在哪里
------------------------------------------------------------

Geant4 训练输出：
    figure/geant4_v2_imaging/

真实实验输出：
    figure/experiment_imaging/

主要图像：
    01_reconstructed_image.png
    02_log_reconstructed_image.png
    03_event_score_histogram.png
    04_event_weight_histogram.png
    05_delta_cos_second_histogram.png
    06_top_event_response_0.png
    06_top_event_response_1.png
    ...

参数文件：
    compton_scorer_v2_params.json

注意：
    相对路径相对于你运行 python 命令时的当前工作目录。
    建议在工程根目录运行：

        python main_geant4_train.py
        python main.py


10. 当前版本的限制
------------------------------------------------------------

1. ComptonEventScorerV2 是线性双头模型。
   可解释性好，但表达能力有限。
   后续可以升级成 MLP。

2. full_deposition_prob 目前依赖 primary_energy 标签训练。
   如果 ROOT 文件没有 primary_energy branch，
   y_full 可能无法训练，只能训练 y_match。

3. 当前 escape event 默认不用于普通 deposited-energy-sum 康普顿成像。
   如果源能量已知，未来可以允许 escape event 使用已知 E0 生成康普顿锥。

4. 当前成像是 weighted backprojection。
   图像会比 MLEM 更糊。
   后续应升级 weighted list-mode MLEM。

5. backscatter 当前默认不枚举。
   如果需要处理 backscatter，需要 allow_backscatter=True 并重新训练。


11. 推荐调试顺序
------------------------------------------------------------

第一步：
    运行：

        python main_geant4_train.py

第二步：
    看 ROOT branch 是否识别成功。
    如果失败，填写 branch_map。

第三步：
    看 hit_df summary：
        hit number
        true event number
        layers

第四步：
    看 candidate 数量：
        train candidates
        test candidates

第五步：
    看 y_match 正样本比例。
    如果正样本极少，减小 event_ids_per_window 或检查 layer/hit 数据。

第六步：
    看 loss 是否下降。

第七步：
    看 score histogram：
        3-hit 不应全部挤在 1；
        2-hit 和 3-hit 都应有高低分布。

第八步：
    看 full_deposition_prob / imaging_weight 分布。
    逃逸事件应被压低。

第九步：
    看 reconstructed image。
    如果图像仍然糊：
        检查 image_plane_z；
        提高 min_score；
        降低 sigma_angle_deg；
        检查 y_full 是否正确；
        检查 ROOT 中 primary_energy 是否存在。


12. 核心设计思想总结
------------------------------------------------------------

本程序的核心不是直接假设：

    E_in = E1 + E2 + E3

而是：

    先学习这个 candidate 是否属于同一条 gamma；
    再学习这个 candidate 是否全能量沉积；
    最后只让高 match_prob 且高 full_deposition_prob 的 event 强烈参与成像。

核心公式：

    imaging_weight = match_prob * full_deposition_prob

Geant4 的 true_event_id 是监督训练的关键：

    同一个 candidate 中所有 hit 的 true_event_id 相同：
        y_match = 1

    否则：
        y_match = 0

full-deposition gate 是处理逃逸事件的关键：

    E_total 接近 primary_energy:
        y_full = 1

    否则:
        y_full = 0

最终目标：

    用 Geant4 truth 训练出可靠的 event scorer；
    再把训练好的 scorer 应用到真实实验数据；
    通过 EventMatcher 和 ComptonConeImager 得到更干净的源图像。