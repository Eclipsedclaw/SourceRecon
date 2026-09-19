# Reconstruction——用户手册

## 编译与运行

新机器首次使用时，先在 V6 根目录执行一次：

```bash
make configure
```

```bash
cd Reconstruction
make
./EIID_Recon_V6 config/recon_config.json
```

编译时会自动生成 `../common/libeiid_common.a`。最终程序名为 `EIID_Recon_V6`。

## 可调参数

配置文件：`config/recon_config.json`。

| 参数 | 含义 |
|---|---|
| `input_events_file` | 精简事件 ROOT 文件 |
| `input_events_tree` | 精简事件所在 Tree |
| `output_result_file` | 重建结果 ROOT 文件 |
| `output_result_tree` | 写入结果文件的 Tree |
| `absolute_efficiency_file` | 网格转换后的绝对效率 ROOT 文件 |
| `absolute_efficiency_tree` | 包含 `cell_index` 和 `efficiency` 的 Tree |
| `healpix_nside` | 重建 HEALPix 分辨率 |
| `healpix_ordering` | 必须为 `RING` |
| `energy_min_MeV` | 候选入射能量下限 |
| `energy_max_MeV` | 候选入射能量上限 |
| `energy_point_count` | 候选能量点数 |
| `iteration_count` | LM-MLEM 迭代次数 |
| `response_sigma_degree` | 角度高斯响应宽度 |
| `denominator_floor` | 判断数值接近零的下限 |
| `event_branches.r1_x` | ch2 相互作用位置 x Branch |
| `event_branches.r1_y` | ch2 相互作用位置 y Branch |
| `event_branches.r1_z` | ch2 相互作用位置 z Branch |
| `event_branches.r2_x` | ch1 相互作用位置 x Branch |
| `event_branches.r2_y` | ch1 相互作用位置 y Branch |
| `event_branches.r2_z` | ch1 相互作用位置 z Branch |
| `event_branches.e1_MeV` | ch2 沉积能量 Branch |
| `result_branches.cell_index` | 展平后的方向—能量单元索引 |
| `result_branches.weight` | 重建强度 |
| `result_branches.healpix_pixel_id` | HEALPix 方向像素编号 |
| `result_branches.theta_degree` | 方向极角，单位度 |
| `result_branches.phi_degree` | 方向方位角，单位度 |
| `result_branches.direction_x` | 单位方向 x 分量 |
| `result_branches.direction_y` | 单位方向 y 分量 |
| `result_branches.direction_z` | 单位方向 z 分量 |
| `result_branches.energy_MeV` | 当前单元的候选能量 |
| `absolute_efficiency_branches.cell_index` | 效率文件中的单元索引 Branch |
| `absolute_efficiency_branches.efficiency` | 绝对效率 Branch，默认名为 `efficiency` |

JSON 中的相对路径均以该 JSON 所在目录为基准。重建网格必须与绝对效率文件的元数据完全一致；若不一致，程序会报错，必须先运行 GridResampler。

默认输出为 `result.root`，可直接交给 Visualization 绘图。
