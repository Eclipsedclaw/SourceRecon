# EIID 阶段 3 响应模型与原型库

## 1. 本阶段范围

阶段 3 建立重建器与具体响应存储之间的稳定边界，完成：

- 单事件天空方向—能量联合稀疏响应；
- 未知入射能量 2-hit 事件的多能量候选；
- 条件接受概率、远场有效面积和有限距离绝对概率的严格分型；
- 响应库元数据、数组校验和原型存储往返；
- backscatter 在 I/O 中保留、在当前正常序列核中显式报告为未启用分量。

本阶段不生成正式 Geant4 响应，也不实现 LM-MLEM 迭代。

## 2. 联合网格索引

事件响应采用稀疏数组保存，联合单元按下式展平：

    cell_index = sky_pixel_index * energy_bin_count + energy_bin_index

重复索引在领域对象构造时合并。正式运行不得把全部事件响应同时转换成稠密
矩阵；to_dense() 仅用于小规模单元测试。

## 3. 灵敏度物理定义

代码使用三个不同的 SensitivityKind，不能用含糊的 s 变量互换：

1. conditional_acceptance_probability，单位 1；
2. effective_area_cm2，单位 cm2；
3. finite_distance_emitted_probability，单位 1。

远场有效面积使用：

    A_eff = A_gen * N_accepted / N_generated

有限距离点源相对总发射量的概率使用：

    s_emitted = (N_accepted / N_generated_in_cone) * Omega_cone / (4*pi)

二者的类型、单位和归一化元数据均随响应库保存。

## 4. 解析响应的限制

AnalyticComptonResponse 是接口联调模型，其响应语义明确记录为：

    prototype_relative_likelihood_not_normalized

ARM 宽度必须由配置显式提供，没有隐藏的固定 5 度默认值。它不包含正式
Doppler broadening、逃逸分布、拓扑概率或绝对归一化，因此不得把阶段 3
输出用于物理结论。

## 5. 原型存储格式

PrototypeNpzJsonResponseStore 使用 arrays.npz 和 manifest.json。该格式明确
标记为 eiid.prototype.npz_json.v1 / prototype_not_formal，只用于验证：

- 能量 bin 边界没有在往返中丢失；
- 灵敏度类型、单位、定义和误差完整；
- 标定数组可扩展；
- SHA-256 能识别不完整或损坏的数组文件；
- manifest 和数组校验完成后最后原子写入 SUCCESS.json，作为完成标记。

正式响应库选择仍是待确认事项。后续选择 HDF5、Zarr、ROOT 或组合格式时，
只新增存储适配器，不修改 EventResponseModel 和重建器接口。
