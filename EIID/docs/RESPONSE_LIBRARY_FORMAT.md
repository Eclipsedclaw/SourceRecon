# EIID 可移植响应库 v1

第一版采用 `portable_npz_json_v1`：JSON manifest 保存物理来源、单位、网格和
数组索引，NPZ 保存数值数组，`SUCCESS.json` 与 SHA-256 共同判定完整性。重建器
只依赖 `ResponseLibrary`，未来增加 HDF5/Zarr adapter 不需要修改 LM-MLEM。

## Geant4 节点统计输入

`build_response_library.py` 接收 NPZ，每一行对应一个天空—能量节点，必需数组：

- `sky_pixel_index`、`energy_bin_index`；
- `generated_count`，必须包含零沉积和未触发 primary；
- `accepted_count`，执行数字化、ch1+ch2 触发和质量筛选后的数量；
- `arm_sigma_deg`，由独立标定样本得到。

可选拓扑数组命名为 `topology_count__<name>`。缺失表示未标定，不能解释为零。
正式构建要求完整覆盖 HEALPix×能量网格；重复、缺失、越界、负数及
`accepted>generated` 均会被拒绝。

## 灵敏度与状态门禁

- 条件接受概率始终保存；
- 远场保存 `A_eff=A_gen*N_accepted/N_generated`，不乘 Ω/4π；
- 有限距离保存 `s_emitted=conditional*Omega/(4*pi)`；
- 不适用的物理量保存为缺失，不以零数组冒充。

初次构建使用 `candidate_unvalidated`。完成独立闭环验证后才可明确设置
`validated_physical`。候选库只有在配置显式 `allow_unvalidated_response=true`
时可做软件验证，输出仍标记不可用于物理。

`validated_physical` 还必须在 metadata.attributes 中提供
`validation_report_sha256`、`validation_dataset_id` 和
`validation_completed_utc`；仅手工修改状态字符串不能通过构建。
