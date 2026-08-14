README.txt
============================================================
SOE1：未知入射能量 2-hit 多圆锥与球面 SOE 联合重建程序说明
============================================================

本文档面向第一次接触本程序的组内同学。即使没有参加此前讨论，也应能
通过本文理解：

    1. SOE1 想解决什么物理问题；
    2. 为什么 ch0 hit 不能直接等价为全吸收；
    3. 2-hit 如何以“多能量、多圆锥”形式进入 SOE；
    4. 3-hit、2-hit 和 ch0-only 在程序中分别承担什么任务；
    5. 实验 TSV 和 Geant4 ROOT 怎样接入同一套重建代码；
    6. 怎样修改所有文件路径并把程序搬到服务器；
    7. 输出文件分别代表什么；
    8. 哪些参数只是当前基线，必须由后续模拟或标定替换；
    9. 正确的验证顺序以及禁止作出的过度结论。

重要说明：

    SOE1 是 D:\CodexForSR\SOE\SOE1 下的全新独立程序。
    它没有在旧 SOE 或 FristArithmetic2.0 的代码上继续堆叠。
    实验 IO 的六文件习惯参考了 FristArithmetic2.0，但内部已经改成
    可保留同 channel 多 hit 的长表对象。

    本地开发不具备服务器上的完整 ROOT 数据与相同 Python 环境。服务器
    批量运行仍必须严格按本文“验证顺序”检查，不应把热点直接解释为真实源。


============================================================
第一部分：项目目标与核心结论
============================================================


1. 要解决的问题
------------------------------------------------------------

当入射 gamma 能量 E0 未知时，一个 2-hit 事件只测得：

    第一次位置 r1
    第二次位置 r2
    第一次沉积能量 E1
    第二次沉积能量 E2

若事件完全吸收，可以近似使用：

    E0 = E1 + E2

计算康普顿角。但若第二次作用后仍有光子逃逸，则：

    E0 > E1 + E2

仅凭该 2-hit 自身无法知道逃逸能量。因此同一 2-hit 并不对应唯一圆锥。

本程序不做以下错误处理：

    不因为末端 hit 在厚 ch0 就宣布事件全吸收；
    不把所有 2-hit 的 E1+E2 当作真实 E0；
    不先猜一个 E0 再把不确定性丢掉；
    不使用 Geant4 primary energy 真值参与未知能源重建。

本程序采用：

    一个 2-hit
        -> 多个候选入射能量
        -> 每个能量有 full/escape 类型权重
        -> 每个能量产生一个不同康普顿圆
        -> SOE 在能量、类型和天空方向之间联合采样


2. 三类事件的分工
------------------------------------------------------------

跨层 2-hit：

    参与方向成像。
    每个事件保留一族能量加权的圆锥。
    它提供的是较宽概率约束，不是确定圆锥。

跨层 3-hit 或更多 hit：

    使用前三个有序 hit 的第二次散射几何恢复 E0。
    它的能量 kernel 通常比 2-hit 窄，在 SOE 中自然成为方向锚点。
    后续可见 hit 的能量仍计入事件总沉积能量。

ch0-only：

    一个事件的所有 hit 都位于 ch0 时，不参与方向图。
    它们的总沉积能量用于建立全局经验能谱先验。
    同一个 ch0-only 事件可以包含多个 ch0 pixel hit。

其他单层事件：

    当前版本既不参与方向成像，也不参与 ch0 能谱，保存为 rejected。


3. 当前实验条件怎样进入程序
------------------------------------------------------------

当前实验近似认为：

    同一瞬间至多一条 gamma 进入探测器并发生作用；
    同一 gamma 的不同 hit 在同一瞬间完成；
    模拟数据可以提供真实 eventID。

因此 SOE1 不再做 FristArithmetic2.0 中的 fake coincidence window 和
多 gamma EventMatcher。实验 EventID 或 Geant4 eventID 直接定义一个
MeasuredEvent。

必须注意：

    event grouping 已知，不代表 hit 作用顺序已知。

当前基线默认不考虑 backscatter，按 layer 递增排序：

    layer 0 = ch2
    layer 1 = ch1
    layer 2 = ch0

如果以后需要处理 backscatter，必须把 order 也变成隐变量，不能继续
沿用 layer 排序。


============================================================
第二部分：2-hit 多圆锥模型
============================================================


1. 康普顿角
------------------------------------------------------------

对某个候选入射能量 E0，第一次沉积为 E1，则：

    E_after = E0 - E1

    cos(theta)
        = 1 - m_ec^2 * [1/(E0-E1) - 1/E0]

其中：

    m_ec^2 = 0.51099895 MeV

只有满足：

    E0 > E1
    -1 <= cos(theta) <= 1

的能量候选才能生成物理圆锥。


2. full 与 escape 分支
------------------------------------------------------------

对全局能量网格中的每个 E_m，SOE1 计算两个分支。

full 分支：

    权重包含：
        全局能谱概率；
        末端 channel 的全吸收先验；
        E_total 与 E_m 的能量分辨率高斯响应；
        Klein-Nishina 相对截面。

escape 分支：

    只允许 E_m >= E_total；
    权重包含：
        全局能谱概率；
        1 - 全吸收先验；
        missing energy 的经验逃逸响应；
        Klein-Nishina 相对截面。

当前解析基线的形式位于：

    soe1/response/event_response.py

其中 ch0 只提高 full_probability，不会把 full_probability 设置为 1。


3. 当前响应参数不是永久真值
------------------------------------------------------------

示例配置中：

    ch0 terminal full probability = 0.25

这个值只是根据当前 662 keV 跨层含 ch0 模拟统计量设置的起始值，不是
材料的普适常数，也不能直接推广到其他能量和入射角。

正式使用应由多能源、多入射角 Geant4 或实验标定建立：

    P(full | E0, channel pair, Edep, geometry)
    P(Edep | E0, escape, channel pair, geometry)
    ARM(delta theta | E0, theta, distance, layer combination)

SOE1 已将这些逻辑集中在 response 子包，替换响应模型时不需要修改 SOE
采样器。


4. ch0-observed 能谱的含义
------------------------------------------------------------

spectrum.mode = "ch0_observed" 时，程序把每个 ch0-only 事件的所有沉积
能量相加，然后在配置的能量网格上做高斯核平滑。

它的优点：

    不需要事先填写单一已知 E0；
    可以利用当前数据中数量很多的 ch0-only 事件；
    对明显的窄谱线可以提供有价值的能量先验。

它的局限：

    这是“观测沉积谱”的经验先验，不是严格响应反卷积；
    逃逸连续谱可能被误当成入射能谱成分；
    不同方向的 ch0 效率差异尚未校正。

如果已经知道候选谱线，应使用：

    spectrum.mode = "configured"

并在 components 中填写多个能量、权重和 sigma。configured 并不要求只有
一条谱线，也不会把单个事件强制归到某条谱线。


============================================================
第三部分：3-hit 几何能量恢复
============================================================


设前三个有序 hit 为：

    (r1, E1)
    (r2, E2)
    (r3, E3)

第二次散射几何角由：

    r2-r1
    r3-r2

求得。设第二次散射前光子能量为 K，则：

    1/(K-E2) - 1/K
        = [1-cos(theta2)] / m_ec^2

解出 K 后：

    E0_recovered = E1 + K

该关系不要求第三个 hit 完全吸收，因此可以处理一部分 3-hit escape。
当 theta2 接近 0、几何位置重合或解不物理时，该事件不会静默退化为
高质量事件，而会在 kernel 阶段被拒绝。

当前使用能量网格表达 E0_recovered 的不确定性：

    weight(E_m)
        ∝ spectrum(E_m)
          * Gaussian(E_m | E0_recovered, sigma_geometry)
          * Klein-Nishina


============================================================
第四部分：2-hit 怎样进入 SOE
============================================================


1. 扩展后的事件状态
------------------------------------------------------------

旧球面 SOE 每个事件只有一个当前方向：

    S_i = u_i

SOE1 中一个事件状态为：

    S_i = (u_i, E_i, c_i)

其中：

    u_i：当前天空方向；
    E_i：当前离散入射能量；
    c_i：full、escape 或 geometry_recovered。

每个事件在每一时刻仍只向天空图贡献一个 origin，保留 SOE 的基本思想。


2. 一次独立 proposal
------------------------------------------------------------

对事件 i：

    1. 按该事件所有 hypothesis 的物理权重抽取 (E_i, c_i)；
    2. 用 E_i 和第一个 hit 的沉积能量计算 theta_i；
    3. 从 ARM 加宽后的 beta 分布抽样；
    4. 沿该圆均匀抽取 phi；
    5. 在 detector frame 生成方向；
    6. 使用该事件时刻的姿态转到 sky frame；
    7. 映射到 HEALPix pixel。

beta 的采样包含球面面积修正：

    p(beta) ∝ ARM(beta-theta) * sin(beta)


3. 为什么接受率仍可使用 SOE count ratio
------------------------------------------------------------

这里不是无条件照搬原接受率。

程序把单事件物理分布定义为：

    q_i(E, c, u | D_i)

每次 proposal 都独立地从这个完整归一化分布抽样。目标后验为：

    pi(S | D)
        ∝ Psi_SOE(counts) * product_i q_i(S_i | D_i)

在独立 Metropolis-Hastings 中：

    目标中的 q_i(new)/q_i(old)

与：

    proposal 的 q_i(old)/q_i(new)

严格抵消，因此接受率只剩 SOE 像素占据数变化。

若旧像素含 d_o 个事件，新像素含 d_n 个事件：

    log R_SOE
        = g(d_n+1) + g(d_o-1) - g(d_n) - g(d_o)

    g(d) = d log(d), d>0
    g(0) = 0

这项设计位于：

    soe1/reconstruction/kernel.py
    soe1/reconstruction/sampler.py

以后若加入局部能量移动、沿圆局部移动、非均匀背景或方向曝光，proposal
不再等于完整单事件 kernel，就必须恢复完整 MH target 与 proposal ratio，
不能只保留 count ratio。


============================================================
第五部分：面向对象模块结构
============================================================


SOE1/
    README.txt
        本说明文档。

    requirements.txt
        Python 依赖。

    main_geant4.py
        Geant4 ROOT 入口，仅解析命令行并调用 SoeApplication。

    main_experiment.py
        实验 TSV 入口，仅解析命令行并调用 SoeApplication。

    config/
        geant4_example.json
        geant4_batch.json
        experiment_example.json

    soe1/
        configuration.py
            JSON 读取、配置校验和可迁移路径解析。

        domain.py
            Hit、MeasuredEvent、EnergyHypothesis、EventKernel、
            EventState 等领域对象。

        io/
            base.py
                EventSource 抽象接口。

            experiment.py
                ch0/ch1/ch2 TSV 和三份刻度表接口。

            geant4.py
                ROOT step 读取、pixel hit 聚合和 eventID 分组；包含面向
                千万 EventID 文件的分块读取和等概率蓄水池抽样。

        physics/
            compton.py
                康普顿角、圆锥轴、3-hit 几何能量和 Klein-Nishina。

        response/
            spectrum.py
                configured/ch0-observed 离散能谱。

            event_response.py
                能量分辨率、全吸收先验、ARM 与多圆锥 kernel。

        geometry/
            direction.py
                带 sin(beta) 修正的 ARM 圆环方向采样。

            attitude.py
                单位姿态与 CSV 四元数姿态接口。

            pixelization.py
                HEALPix 包装类。

        reconstruction/
            kernel.py
                独立单事件 proposal。

            sampler.py
                球面 SOE 链、burn-in、thinning 和后验统计。

        application/
            pipeline.py
                组装 IO、响应、姿态、采样和输出的高层应用类。

            batch.py
                遍历模拟目录、建立逐组配置、断点续跑和错误清单。

        analysis/
            metadata.py
                从文件名读取能量、距离和方位真值，仅用于事后评估。

            dataset_report.py
                单组平面投影、能量/full-escape 图、dashboard 和质量指标。

            batch_report.py
                跨能量、距离、方位的折线、热图、总览和图片矩阵。

        diagnostics/
            plots.py
                使用无窗口 backend 保存球面图和能谱图。

            writer.py
                CSV、NPY 和 JSON 输出。

    tests/
        test_compton_kinematics.py
        test_domain.py
        test_soe_ratio.py
            服务器端可执行的最小运动学、layer 合并和接受率回归测试。


============================================================
第六部分：实验数据接口
============================================================


1. 六个输入文件
------------------------------------------------------------

与 FristArithmetic2.0 一致，实验配置需要：

    ch0.tsv
    ch1.tsv
    ch2.tsv

    calibration_ch0.tsv
    calibration_ch1.tsv
    calibration_ch2.tsv

所有地址在：

    config/experiment_example.json

的：

    input.paths
    input.calibration_paths

中修改。代码中没有硬编码实验文件地址。


2. 默认实验 hit 列
------------------------------------------------------------

    EventID
    PixelID
    TotalEnergy
    pos_x_mm
    pos_y_mm
    z

如果文件列名不同，只修改：

    input.columns

不需要修改 Python。

如果实验文件有逐事件时间，可增加：

    "time_ns": "实际时间列名"

如果使用姿态表，每个可成像事件必须有时间。


3. 默认刻度列
------------------------------------------------------------

    PixelID
    a(keV/ADC)
    b(keV)

刻度公式：

    energy_keV
        = TotalEnergy * a(keV/ADC) + b(keV)

    energy_MeV
        = energy_keV / 1000

列名可在 input.calibration_columns 中修改。


4. 同 channel 多 hit
------------------------------------------------------------

SOE1 不再把三个 channel outer merge 成宽表，而是先保留长表 Hit 对象。
因此读入阶段：

    同一 EventID、同一 channel、不同 PixelID

不会产生笛卡尔积。

当前 SOE 运动学不推断同一 detector layer 内多个 pixel 作用的先后顺序。
在进入事件分类前，程序会把同一 layer 的多个 pixel hit 合成为一个有效
layer hit：

    能量求和；
    位置取沉积能量加权质心；
    时间取最早值。

因此三层硬件最终至多产生 3-hit 事件。该处理保持总沉积能量，但质心不是
真实逐次作用位置；如果未来要利用同层多 hit，必须增加层内 order 模型，
不能直接把 pixel 行顺序当成物理顺序。

当前不尝试分解同一 TSV 行内已经被电子学合并的多次作用。


============================================================
第七部分：Geant4 ROOT 接口
============================================================


1. 示例 branch
------------------------------------------------------------

示例配置读取：

    eventID
    chamberID
    pixelID
    eDep_MeV
    x_post
    y_post
    z_post
    stepID
    time_ns

全部 branch 名可在：

    input.branches

中修改。


2. step-to-hit
------------------------------------------------------------

程序先删除：

    eDep_MeV <= minimum_hit_energy_mev

再按：

    eventID + chamberID + pixelID

聚合：

    energy：step eDep 求和；
    x/y/z：按 step eDep 加权平均；
    time：最早 time_ns；
    order：最小 stepID，只保存为开发期辅助字段。

程序检查聚合前后总沉积能量是否守恒。


3. chamber/layer/channel
------------------------------------------------------------

当前示例：

    chamberID 0 -> layer 0 -> ch2
    chamberID 1 -> layer 1 -> ch1
    chamberID 2 -> layer 2 -> ch0

配置位置：

    input.chamber_to_layer
    input.layer_to_channel

正式运行前必须结合 geometry QA 再确认一次，不能只凭数字名字猜测。


4. Geant4 truth 的使用边界
------------------------------------------------------------

SOE1 使用 eventID 把同一条 primary gamma 的可见 hit 分到同一个事件。

当前重建不读取：

    primary energy
    full/escape truth label
    source direction truth

因此真实 E0 不会泄漏到 2-hit hypothesis。

示例 order_mode 使用 layer。stepID 是 track 内编号，不能自动等价为完整
gamma 历史的全局作用顺序。若以后确实要使用 truth order，应先在 ROOT 中
加入一个明确、跨 track 可比较的 interaction order branch。


============================================================
第八部分：路径与服务器迁移
============================================================


1. 路径规则
------------------------------------------------------------

所有输入、姿态和输出路径都写在 JSON。

绝对路径：

    Linux:
        /home/user/project/data.root

    Windows:
        D:/data/data.root

相对路径：

    相对于 JSON 配置文件所在目录，而不是当前 shell 目录。

例如配置文件位于：

    SOE1/config/geant4_example.json

则：

    "../../../20260714_lyso.root"

会解析到 CodexForSR 根目录中的 ROOT 文件。


2. 建议服务器目录
------------------------------------------------------------

    project/
        SOE1/
        data/
            simulation.root
            experiment/
        results/

可以复制示例配置为：

    server_geant4.json
    server_experiment.json

只修改路径和参数，保留示例文件作为参考。


============================================================
第九部分：姿态接口
============================================================


1. 单位姿态
------------------------------------------------------------

地面固定坐标或最初几何测试：

    "attitude": {
        "mode": "identity"
    }

此时 detector direction 直接当作 sky direction。


2. CSV 四元数
------------------------------------------------------------

配置形式：

    "attitude": {
        "mode": "csv_quaternion",
        "path": "/server/path/to/attitude.csv",
        "separator": ",",
        "time_scale_to_ns": 1000000000.0,
        "maximum_time_difference_ns": 1000000.0,
        "conjugate": false,
        "columns": {
            "time": "time_s",
            "qx": "qx",
            "qy": "qy",
            "qz": "qz",
            "qw": "qw"
        }
    }

程序按最近时刻选择姿态。

四元数约定：

    (qx, qy, qz, qw)
    detector frame 主动旋转到 sky frame

如果姿态文件提供相反变换，可设置：

    conjugate = true

但必须用已知源方向验证正负号。


============================================================
第十部分：安装与运行
============================================================


1. Python
------------------------------------------------------------

当前服务器环境：

    Python 3.8

SOE1 源码兼容该环境。由于新版 healpy 已不再支持 Python 3.8，
requirements.txt 固定使用：

    healpy==1.16.1

安装：

    pip install -r requirements.txt

对于当前 Conda py38 环境，更推荐使用 conda-forge 的预编译包：

    /home/ezqi/miniconda3/bin/conda install -n py38 \
        -c conda-forge healpy=1.16.1

依赖：

    numpy
    pandas
    matplotlib
    uproot
    awkward
    healpy
    pytest

实验 TSV 模式本身不读取 ROOT，但当前 requirements 为两种入口统一列出
依赖。

安装完成后建议先在 SOE1 目录执行：

    pytest -q

这些测试在交付编写阶段未执行，需要由服务器环境完成。


2. Geant4
------------------------------------------------------------

进入 SOE1 目录：

    python main_geant4.py --config config/geant4_example.json

单文件配置仍使用 input.type = "geant4_root"。


3. jcding 全目录批处理
------------------------------------------------------------

批量配置已经写在：

    config/geant4_batch.json

默认读取：

    /data/data/simulation/compton_camera_pixel/jcding

并匹配：

    b1output_gamma_*MeV_z*m_*.root

如果服务器目录变化，只修改 root_directory；ROOT 不需要复制进 SOE1。
在 SourceRecon 仓库根目录运行，并把日志放在 SOE 文件夹：

    /home/ezqi/miniconda3/envs/py38/bin/python -u \
        SOE/SOE1/main_geant4.py \
        --config SOE/SOE1/config/geant4_batch.json \
        2>&1 | tee SOE/jcding_batch.log

程序按文件名自动读取：

    能量：0.300、0.400、...、1.500 MeV
    距离：z0.5m、z1m、z2m
    方位：center、xp、xm、yp、ym

默认真值坐标约定写在配置中：

    center_direction_detector = [0, 0, -1]
    horizontal_axis_detector = [1, 0, 0]
    vertical_axis_detector = [0, 1, 0]
    source_offset_angle_deg = 15
    generated_event_count_per_file = 10000000

如果 Geant4 对 xp/xm/yp/ym 的坐标定义不同，只修改这三个向量和角度。
这些真值只用于画星号和计算误差，不会进入 SOE 重建。

每个文件有千万级 EventID。批量配置默认：

    按 250 MB 分块读取 ROOT；
    扫描完整文件以保留真实总事件统计；
    从全部成像事件中等概率抽 2000 个用于 SOE；
    从全部 ch0-only 事件中等概率抽 100000 个建立能谱。

因此不会只偏向文件开头。抽样上限可修改：

    maximum_imaging_events
    maximum_spectroscopy_events

设为 null 表示全部保留，但对当前大文件会显著增加内存、磁盘和运行时间。
run_summary.json 同时记录有正沉积的事件总数和实际使用数。ROOT step 表无法
凭空恢复没有留下任何 row 的 EventID，因此“占全部 1000 万初级事件的效率”
使用 generated_event_count_per_file 作为分母；如果某批模拟的初级事件数
不同，必须修改该项。

批量配置使用 healpix_nside = 16，是因为当前 ARM sigma 约 4--5°，且每组
默认只抽 2000 个成像事件；nside = 32 会让图过度稀疏，不等于获得了更高
真实角分辨率。800 sweeps 用于第一轮全条件比较。正式结论仍应提高事件数、
sweeps，并用多个 random_seed 检查误差和 R68 是否稳定。

batch.skip_completed_datasets = true 时，已有 quality_metrics.json 的组会
跳过，可在服务器中断后直接用同一条命令续跑。单组失败默认记入错误表并
继续下一组。

第一次建议把：

    batch.maximum_files = 1

先完整跑通一组并确认 ROOT branch、方向正负号和图像。确认后恢复为 null，
再执行全批次。不要用只跑一组的结果评价跨能量趋势。


4. 实验
------------------------------------------------------------

先修改：

    config/experiment_example.json

中的六个文件路径，再运行：

    python main_experiment.py --config config/experiment_example.json


5. 能谱已知为若干候选线时
------------------------------------------------------------

将 spectrum 改为：

    "spectrum": {
        "mode": "configured",
        "minimum_energy_mev": 0.10,
        "maximum_energy_mev": 2.00,
        "energy_step_mev": 0.01,
        "configured_component_sigma_mev": 0.02,
        "probability_floor": 1e-12,
        "components": [
            {
                "energy_mev": 0.662,
                "weight": 1.0,
                "sigma_mev": 0.02
            },
            {
                "energy_mev": 1.173,
                "weight": 0.5,
                "sigma_mev": 0.03
            }
        ]
    }

这只是总体能谱先验，每个 2-hit 仍会保留 full/escape 概率，不会因为某条
谱线存在就被宣布全吸收。


============================================================
第十一部分：输出文件
============================================================


output.directory 下生成：

单文件模式仍直接生成下面的 numerical 文件。批量模式采用清楚的分层结构：

    output/jcding_batch/
        batch_manifest.json

        datasets/
            E0p662MeV__z0p5m__center/
                dataset_metadata.json
                quality_metrics.json
                event_summary.csv

                numerical/
                    posterior_mean_map.npy
                    posterior_variance_map.npy
                    sky_map.csv
                    spectrum_prior.csv
                    event_hypothesis_posterior.csv
                    final_event_states.csv
                    run_summary.json
                    configuration_snapshot.json
                    posterior_mean_sky_map.png
                    spectrum_prior.png

                figures/
                    01_all_sky_mollweide.png
                    02_front_hemisphere_flat.png
                    03_source_centered_zoom.png
                    04_radial_containment.png
                    05_energy_prior_and_posterior.png
                    06_full_escape_probability.png
                    07_event_energy_reconstruction.png
                    08_source_zoom_uncertainty.png
                    09_dataset_dashboard.png

        overall/
            batch_summary.csv
            batch_summary.json
            failed_datasets.csv
            failed_datasets.json

            figures/
                01_angular_error_vs_energy.png
                02_r68_vs_energy.png
                03_energy_mae_vs_energy.png
                04_event_efficiency.png
                05_expected_vs_reconstructed.png
                06_angular_error_heatmap.png
                07_r68_heatmap.png
                08_overall_dashboard.png

            montages/
                distance_0.5m_front_maps.png
                distance_1m_front_maps.png
                distance_2m_front_maps.png

最先建议查看：

    每组：figures/09_dataset_dashboard.png
    同距离全部组：overall/montages/
    全部条件结论：overall/figures/08_overall_dashboard.png
    精确数值：overall/batch_summary.csv

02_front_hemisphere_flat.png 把探测器朝向的大半球正投影到单位圆盘，避免
必须在三维球面上判断热点。03_source_centered_zoom.png 以模拟真值为原点，
横纵轴直接表示角偏差 degree；白色星号是真值，黑色叉号是后验质心。

quality_metrics.json 和 batch_summary.csv 包含：

    后验质心与峰值的方向误差；
    R50、R68、R90；
    真值附近 10°/20° 相对均匀天空的增强倍数；
    单事件能量 bias、MAE、RMSE；
    full/escape 分类 precision、recall；
    成像事件占初级事件/正沉积事件的比例、有效 kernel 比例和 SOE 接受率。

注意 R68 描述“围绕真值包含 68% 后验所需的半径”，它会同时受到主峰宽度、
错误热点和全局背景影响，比只报告最亮 pixel 更严格。

posterior_mean_map.npy
    burn-in 后各保存样本的 HEALPix 像素计数平均。

posterior_variance_map.npy
    对应像素计数后验方差。

sky_map.csv
    每个 HEALPix pixel 的：
        pixel_index
        x/y/z 单位向量
        longitude/latitude degree
        posterior mean
        posterior variance
        final count

posterior_mean_sky_map.png
    posterior mean HEALPix 图的 Mollweide 投影。使用 Agg backend，服务器
    不需要图形桌面。

spectrum_prior.csv
    进入事件 kernel 之前的全局能谱先验。

spectrum_prior.png
    同一能谱先验的快速诊断图。

event_hypothesis_posterior.csv
    每个事件每个能量/类型 hypothesis 的：
        independent prior probability
        SOE posterior visit fraction
        incident energy
        full/escape/geometry_recovered
        scatter angle
        ARM sigma
        missing energy 等诊断量

    该文件是判断 2-hit 是否真的从多圆锥收缩到少数能量的重要依据。

final_event_states.csv
    链最后状态，只用于诊断。正式天空结果应看 posterior mean，不能只看
    最后一帧。

run_summary.json
    输入事件数、kernel 数、2-hit/3-hit 数、接受率、保存样本数和 seed。

configuration_snapshot.json
    本次运行实际使用的完整配置快照。


============================================================
第十二部分：第一次运行必须采用的验证顺序
============================================================


第一步：只检查 IO summary

    event_count
    imaging_event_count
    spectroscopy_event_count
    rejected_event_count
    hit_count

确认 ch0-only 没有进入方向事件，跨层事件没有被丢到 spectroscopy。


第二步：检查能量守恒和单位

Geant4：

    step eDep sum == aggregated hit energy sum

实验：

    确认 ADC -> keV -> MeV；
    确认没有把 keV 数值当 MeV。


第三步：检查圆锥轴正负号

用已知方向单点源确认热点出现在真实源方向，而不是反方向。


第四步：configured 单能源 oracle

先使用模拟已知单能数据，将 spectrum.mode 暂时设为 configured 单线。
这一步只验证：

    康普顿公式；
    hit 顺序；
    圆锥轴；
    ARM；
    HEALPix；
    SOE count ratio。

它不是未知能源性能结果。


第五步：四组消融比较

    A. 只用可恢复能量的 >=3-hit；
    B. >=3-hit + truth full 2-hit，作为 oracle 上限；
    C. 错误地把所有 ch0 2-hit 当全吸收；
    D. 当前多圆锥 full/escape SOE。

重点比较：

    方向误差；
    峰宽；
    信噪比；
    假热点数量；
    能量后验偏差；
    不同 seed 稳定性。


第六步：ch0-observed 未知能量

只有前五步正确后，才启用 ch0_observed，并检查：

    spectrum_prior.csv 是否出现合理峰；
    escape continuum 是否产生假谱线；
    2-hit 后验是否无理由过度集中；
    结果是否依赖 KDE bandwidth。


第七步：空场与均匀背景

SOE 的聚集机制可能把随机事件强化成热点。必须使用：

    无点源；
    均匀天空；
    弱源 + 背景；

测试虚假聚集，不能仅用强单点源证明算法有效。


第八步：姿态旋转测试

探测器和源整体旋转后，天空结果应做相同旋转；峰宽和相对强度不应因坐标
表示发生变化。


============================================================
第十三部分：重要参数怎样理解
============================================================


spectrum.minimum/maximum_energy_mev
    允许的入射能量范围。范围过窄会截断真值，过宽会增加 2-hit 退化性。

spectrum.energy_step_mev
    离散能量间隔。不应远小于真实能量分辨率。

spectrum.kde_bandwidth_mev
    ch0-only 沉积谱平滑宽度。必须做灵敏度分析。

response.full_absorption_probability_by_terminal_channel
    末端 channel 的初始 full 先验，不是分类结果。

response.escape_energy_scale_mev
    当前解析逃逸 missing-energy 分布尺度，应由模拟响应替换。

response.three_hit_geometry_fractional_sigma
    3-hit 几何 E0 恢复的不确定度。

response.arm_sigma_deg_by_hit_count
    2-hit/3-hit 的 ARM sigma，不是 FWHM。

reconstruction.healpix_nside
    像素数为 12*nside^2。像素角尺度不应明显小于 ARM。

reconstruction.sweeps
    总 sweep 数；一个 sweep 平均更新每个事件一次。

reconstruction.burn_in_sweeps
    丢弃的初始链段。

reconstruction.thinning_sweeps
    burn-in 后每隔多少 sweep 保存一次。

reconstruction.random_seed
    完整控制初始化和 proposal，便于复现。


============================================================
第十四部分：当前限制
============================================================


1. 当前默认 layer 递增顺序，不处理 backscatter 和未知 hit order。

2. ch0-observed 是经验谱先验，不是完整 detector-response 反卷积。

3. 当前 full/escape 响应是可配置解析基线，不是多维标定响应库。

4. 当前背景和方向曝光没有进入目标后验。

5. 所有 imaging event 向 SOE count 图贡献一个 origin。极低信息事件和背景
   可能被聚集机制强行吸入热点；未来应加入 signal/background 隐变量。

6. 当前使用全局能谱 p(E)，隐含不同天空方向共享同一总体谱。如果多个源
   的能谱明显不同，后续应升级为空间-能谱联合强度模型，而不是简单增加
   能量 bin 后继续使用同一 d_j。

7. >=3-hit 当前只用前三个有序 hit 的第二散射恢复 E0，尚未实现所有 hit
   序列的完整多重康普顿概率模型。

8. 当前自动图只用于快速 QA；正式定量分析应读取 sky_map.csv 或 NPY，
   不能从 PNG 颜色直接读数。


============================================================
第十五部分：后续替换响应模型时的接口
============================================================


建议保留以下边界：

EventSource.read()
    只返回 InputDataset。

SpectrumPriorFactory.build()
    只返回 DiscreteSpectrumPrior。

EventKernelFactory.build()
    只把 MeasuredEvent 转为 EventKernel。

IndependentEventProposal.propose()
    只从单事件完整 kernel 抽状态。

SphericalSoeSampler.run()
    只负责 SOE 链和后验统计。

例如未来加入 Geant4 表格响应时，应新增：

    TabulatedDetectorResponse

替换 EventKernelFactory 内部权重计算，而不是把 ROOT truth、插值或文件读取
直接写进 sampler.py。


============================================================
第十六部分：必须长期遵守的原则
============================================================


1. ch0 hit 提高全吸收概率，但永远不等于全吸收证明。

2. 2-hit 未知能量对应一族圆锥，不能未经概率建模压缩为一个圆锥。

3. Geant4 eventID 可以用于事件分组，但 primary energy/full label 不能泄漏
   到未知能源推断。

4. event grouping 已知不等于作用顺序已知。

5. step 不等于 hit；必须先按可观测像素响应聚合。

6. ch0-only 可用于谱学，但没有跨层方向基线，不能进入天空 count 图。

7. 原 SOE count ratio 只有在当前“完整独立事件 kernel proposal”条件下才
   能直接使用；修改 proposal 后必须重新推导 MH。

8. 后验平均图比最后一次链状态可靠。

9. 热点不等于真实源；必须通过空场、背景、消融和多 seed 测试。

10. 示例响应参数只是起点，正式结果必须使用多能源、多角度模拟或标定。
