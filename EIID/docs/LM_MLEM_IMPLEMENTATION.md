# EIID 阶段 4 稀疏 LM-MLEM 实现

## 1. 更新公式

当前实现遵循设计基线：

    f_new = f / sensitivity * sum_i[R_i / (R_i dot f + b_i)]

事件响应保持稀疏，仅访问每个事件支持的联合单元。灵敏度为零或低于配置下限
的单元固定为零，不执行除法。

## 2. 数值保护

- 事件分母下限由 denominator_floor 配置；
- 灵敏度下限由 sensitivity_floor 配置；
- 初始图像只放在非零灵敏度支撑上；
- 非有限值、负值和更新后全零会明确失败；
- 空数据集、重复 event_id 和不一致联合网格会在迭代前拒绝；
- 固定背景同时区分逐事件密度和背景期望总计数。

## 3. 对数似然与早停

记录的 list-mode Poisson 对数似然为：

    sum_i log(R_i dot f + b_i) - sum_j sensitivity_j * f_j - B_total

支持最大迭代数、似然相对变化和图像 L1 相对变化早停，并要求配置的连续
patience 次数。每次运行保存最终 stop_reason。

## 4. 每次迭代记录

iteration_metrics.jsonl 当前包含：

- Poisson 对数似然及相对变化；
- 联合图像总强度；
- 图像 L1、L2 和最大相对变化；
- 天空边缘与能谱边缘 L1 变化；
- 联合峰值、天空像素和能量 bin 索引；
- 有效事件、零响应事件和无效分母计数；
- 事件分组贡献；
- 单次与累计运行时间、吞吐量；
- 进程 RSS 和系统可用内存。

初始状态、前若干迭代、配置间隔和最终状态保存为压缩 NPZ checkpoint。

## 5. 当前验证边界

stage4_lmmlem_smoke 使用 12×29 联合网格中的两个非零单元和一个 synthetic
稀疏响应矩阵，验证公式、似然单调性、停止条件和输出生命周期。它没有使用
正式 Geant4 响应，不能生成物理结论。

