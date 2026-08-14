# EIID 阶段 5 端到端原型与可视化

## 1. 数据流

阶段 5 首次闭合以下软件链：

    实验 TSV 输入
      -> 统一 MeasuredEvent
      -> 数字化后 ch1+ch2 触发
      -> 解析康普顿稀疏事件核
      -> HEALPix × 0.1--3.0 MeV 联合 LM-MLEM
      -> 数值结果、迭代遥测、checkpoint 和 PNG

模拟和实验仍使用相同领域事件，但各自的输入适配器没有合并。

## 2. HEALPix 和显示坐标

RING ordering 现在具有纯 NumPy 像素中心和方向索引后备实现。若未安装
healpy，RING 网格仍可运行；NESTED ordering 仍要求 healpy。

相机正前方使用配置中的 camera_boresight_source_direction，本项目为 -Z。
显示向上方向由 visualization.display_up_direction 显式配置，stage5 smoke
使用 +Y。二者建立相机显示坐标，因此正前方位于全天图和正交投影中心。

raw skymap 通过最近 HEALPix 像素栅格化，以填充像素形式显示，不使用散点。
smoothed skymap 使用球面角距离高斯核，sigma 来自配置并保持总强度。
纯 NumPy 平滑按 visualization.smoothing_chunk_size 分块，并在像素数超过
visualization.maximum_numpy_smoothing_pixels 时明确停止，防止距离矩阵导致
内存无界增长。正式高分辨率任务应安装并接入经过验证的高效球面平滑后端。

## 3. 当前输出

每个 run 至少输出：

- 相机正前方居中的全天 raw skymap；
- 相机前半球 raw 正交投影；
- 相机前半球 smoothed 正交投影；
- 重建能谱；
- 方向—能量联合分布；
- 似然、图像变化和能谱变化收敛图；
- 总览 dashboard；
- final_joint_image.npz；
- event_summary.csv；
- dataset_metadata.json；
- reconstruction_summary.json；
- 全部迭代遥测和配置化 checkpoint。

文件名来自 visualization.file_names 和 output.file_names。

## 4. 中断恢复边界

阶段 5 支持从失败或中断 run 的最新完整 checkpoint 续跑。指定父 run_id 后，
程序只读父目录，校验 checkpoint 图像有限且非负，然后创建新的 run_id 继续迭代。
新 manifest 记录父 run_id、checkpoint 路径和迭代号；原运行目录不会被覆盖。

服务器入口：

    EIID_RESUME_FROM_RUN_ID=<失败或中断的_run_id> \
    EIID_PYTHON=/home/ezqi/miniconda3/envs/py38/bin/python \
      bash scripts/run_stage5_end_to_end_server.sh

带 SUCCESS.json 的 run 不允许续跑。生产批处理现已实现多数据集调度、失败清单、
按内存动态并发和跳过已完成数据集，详见 BATCH_PROCESSING.md。

## 5. 必须遵守的限制

当前 AnalyticComptonResponse 是未归一化相对似然，阶段 5 使用的灵敏度只是
事件核联合支撑上的 prototype 单位数组。因此：

- 输出只能验证数据流、坐标、稀疏算法和绘图；
- 能谱峰、方向峰和强度不得解释为物理测量；
- 配置必须显式设置 allow_nonphysical_response_for_smoke=true；
- 所有图片标题和摘要均标记 PROTOTYPE / physical_use_allowed=false。

正式物理分析必须等待 Geant4 标定的混合响应和匹配灵敏度接入。
