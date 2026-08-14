EIID 康普顿相机联合能量—方向重建程序
========================================

1. 项目定位
-----------

EIID（Energy–Imaging Integrated Deconvolution）在离散的天空方向 × 入射
能量联合空间中，使用响应函数 R(d|Omega,E) 和灵敏度 s(Omega,E) 对事件进行
LM-MLEM 重建。未知入射能量的 2-hit 事件不会被预先压缩成一个确定圆锥，而是
以多个候选能量和方向的概率响应参与联合估计。

本目录是独立的新项目。不会在 SOE1、SOE1.2 或原有
compton_satellite_sim 上直接开发。两份设计基线位于 docs/：

  - EIID_ALGORITHM_DESIGN.md
  - GEANT4_RESPONSE_DESIGN.md

“已确定决策”是实现约束；暂定方案必须保留替换接口；待确认参数只能出现在
显式配置和决策记录中，不能作为隐藏常量写死。

2. 当前实现状态
---------------

阶段 1 至阶段 5 的原型闭环已完成：

  - Python 3.8+ 工程骨架；
  - JSON/YAML 配置读取与第一版约束校验；
  - 模拟/实验共用的 digitized hit、event、dataset 领域对象；
  - 模拟真值独立封装，便于防止真值泄漏；
  - Geant4 坐标约定：传播 +Z、相机正前方来源方向 -Z；
  - ch1+ch2 数字化有效 hit 触发策略；
  - 康普顿运动学和 HEALPix/能量网格基础对象；
  - 服务器限线程、实时日志和内存保护参数的指令模板；
  - 标准库 unittest/pytest 兼容测试。

阶段 2 已增加：

  - legacy Geant4 `Tree1` 的可配置分支和流式分块读取；
  - 跨 ROOT 分块 event 尾部暂存；
  - step-to-deposit 能量守恒聚合；
  - 独立 `TruthDigitizer` 和 digitized event builder；
  - 实验 CSV/TSV 长表输入；
  - 直接 MeV 和逐像素线性 ADC 标定两种模式；
  - 统一输入后的独立 ch1+ch2 触发流水线；
  - 未触发事件保留在 rejected 视图中，不从原数据集删除。

阶段 3 已增加：

  - 与存储格式无关的 EventResponseModel 抽象接口；
  - 天空方向×能量联合空间的单事件稀疏响应；
  - 未知入射能量 2-hit 事件的多能量候选解析核；
  - 条件接受概率、A_eff 和有限距离 s_emitted 的严格分型；
  - 正确计入 Omega/(4*pi) 的有限距离灵敏度估计；
  - 带 SHA-256 和完成标记的 prototype NPZ+JSON 响应库往返。

阶段 4 已增加：

  - logs、runs 和 response_campaign 共用的唯一 run_id；
  - 配置 SHA-256、运行 manifest、配置快照以及 SUCCESS/FAILURE 标记；
  - 稀疏 list-mode MLEM 更新器和零灵敏度/极小分母保护；
  - Poisson 对数似然、图像/能谱变化、时间、内存和停止原因遥测；
  - 初始、前期、间隔与最终迭代 checkpoint；
  - synthetic 小矩阵似然单调性和主次联合单元恢复验证。

阶段 5 已增加：

  - 实验输入到联合 LM-MLEM 的端到端 main_experiment.py；
  - 无 healpy 时可用的纯 NumPy HEALPix RING 后备；
  - 以相机正前方 -Z 为中心的像素填充 raw/smoothed skymap；
  - 能谱、方向—能量联合分布、收敛图和 dashboard；
  - final_joint_image、event_summary、dataset metadata 和重建摘要；
  - 从失败或中断 run 的最新完整 checkpoint 续跑，并为续跑生成新的 run_id。

生产链已增加：

  - portable_npz_json_v1 响应库、SHA-256 与状态门禁；
  - Geant4 节点统计到条件概率、A_eff 或 s_emitted 的响应构建器；
  - hybrid_monte_carlo_arm_v1 混合响应核；
  - 十三类可配置图片和 Fisher 对角近似能谱误差；
  - 数据集多进程、动态内存容量、保护性终止、重试、checkpoint 恢复；
  - 跳过已完成数据集、批 manifest、内存遥测和失败清单；
  - main_experiment.py、main_geant4.py 和 main_batch.py 三个稳定入口。

软件生产链已闭合。正式物理结果仍要求外部离线 Geant4 campaign 提供包含零 hit
primary 分母、经过独立验证并标记 validated_physical 的响应库。

3. 已确定物理约定
-----------------

  - 第一版能量范围：0.1–3.0 MeV；
  - chamberID 0/1/2 -> ch2/ch1/ch0；
  - 正常前向层序：ch2 -> ch1 -> ch0；
  - Geant4 探测器堆叠/入射传播方向：+Z；
  - 相机正前方的天空来源方向：-Z；
  - 来源方向与传播方向相反；
  - 触发：数字化后 ch1 与 ch2 同时存在有效 hit；
  - ch0 不是触发必要条件，也不自动代表全吸收；
  - backscatter 不得在 I/O 层永久删除；
  - Geant4 只生产离线响应，不进入每次 EIID 迭代。

4. 本地基础验证
---------------

无需安装 pytest 即可运行：

  python -u scripts/validate_foundation.py \
    --config config/examples/foundation_smoke.json

运行全部标准库测试：

  python -m unittest discover -s tests -p "test_*.py" -v

安装开发依赖后也可以：

  python -m pytest -q

5. 服务器运行
-------------

完整指令集见 SERVER_COMMANDS.txt。服务器命令统一遵守：

  - 唯一项目根目录为 /home/ezqi/labwork/SourceRecon/EIID；
  - 输入、响应库、结果、日志和 checkpoint 均位于该目录下；

  - Python 使用 -u，保证日志及时刷新；
  - 数值库内部线程默认限制为 1；
  - 数据集级 worker 才是主要并行层；
  - 使用 2>&1 | tee -a 同时输出到终端和日志；
  - Bash 使用 set -o pipefail，不能让 tee 隐藏 Python 的失败退出码；
  - worker 数是上限，实际并发由内存保护器动态限制；
  - 每个数据集独立状态、失败记录、checkpoint 和完成标记。

当前可运行的服务器基础验证脚本为 scripts/run_foundation_server.sh。

阶段 2 输入链验证：

  python -u scripts/validate_stage2_input.py \
    --config config/examples/experiment_delimited_smoke.json

服务器上推荐使用自动创建日志目录并同时输出到终端和日志的封装入口：

  EIID_PYTHON=/home/ezqi/miniconda3/envs/py38/bin/python \
    bash scripts/run_stage2_input_server.sh

阶段 3 响应接口与归一化验证：

  EIID_PYTHON=/home/ezqi/miniconda3/envs/py38/bin/python \
    bash scripts/run_stage3_response_server.sh

该入口产生的响应库明确标记为 synthetic prototype，不能用于正式物理分析。

阶段 4 运行生命周期与 LM-MLEM 验证：

  EIID_PYTHON=/home/ezqi/miniconda3/envs/py38/bin/python \
    bash scripts/run_stage4_lmmlem_server.sh

该入口自动生成 run_id；日志、运行目录、配置快照、迭代遥测和 checkpoint
使用同一编号。

阶段 5 实验输入端到端原型和图片验证：

  /home/ezqi/miniconda3/envs/py38/bin/python -m pip install -e '.[visualization]'

  EIID_PYTHON=/home/ezqi/miniconda3/envs/py38/bin/python \
    bash scripts/run_stage5_end_to_end_server.sh

阶段 5 图片和峰值只能用于软件闭环检查，不能作为正式物理结果。

6. 配置规则
-----------

所有路径、ROOT 树名/分支名、通道映射、坐标、网格、迭代参数、并行度和输出
选项最终都必须由 JSON/YAML 或命令行覆盖提供。相对路径以配置文件所在目录为
基准，并经过项目根目录边界检查。示例配置中的 smoke 参数只用于基础验证，
不代表飞行标定参数。

第一版虽然固定在 0.1–3.0 MeV，范围仍必须显式写入配置；第一版配置校验器会
拒绝其他范围，避免无意偏离设计基线。
