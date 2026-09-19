# Reconstruction——用户手册

```text
Reconstruction/{config,include,src,io,tests} -> EIID_Recon_V9
```

## 编译与运行

新机器首次使用时，先在 V9 根目录执行一次：

```bash
make configure
```

```bash
cd Reconstruction
make
./EIID_Recon_V9 config/recon_config.json
```

编译时会自动生成公共库和响应核库。最终程序名为 `EIID_Recon_V9`。

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

V9 新增的 `response_kernel` 对象：

| 参数 | 含义 |
|---|---|
| `type` | `fixed_gaussian`、`voigt`、`double_gaussian`、`gaussian_lorentzian_mixture` 或 `histogram` |
| `fixed_sigma_degree` | 固定高斯宽度 |
| `calibration_file` | ResponseCalibration 输出的 ROOT 文件 |
| `parameter_tree` | 标定模型参数 Tree |
| `histogram_name` | 经验三维 PDF 名 |

示例为 `recon_config.json`、`recon_voigt.json`、`recon_double_gaussian.json` 和 `recon_gaussian_lorentzian_mixture.json`。旧 JSON 不含该对象时仍自动使用固定高斯。

JSON 中的相对路径均以该 JSON 所在目录为基准。重建网格必须与绝对效率文件的元数据完全一致；若不一致，程序会报错，必须先运行 GridResampler。

V9 根目录下的推荐命令为 `make reconstruct-eligible`。它读取 `runs/latest/calibration/model_status.json`，只运行全部必需分箱均收敛的模型。默认输出分别写入 `runs/latest/reconstruction/result_<model>.root`。

只检查外部事件文件而不重建：

```bash
./Reconstruction/EIID_Recon_V9 \
  --validate-events-only Reconstruction/config/recon_double_gaussian.json
```
