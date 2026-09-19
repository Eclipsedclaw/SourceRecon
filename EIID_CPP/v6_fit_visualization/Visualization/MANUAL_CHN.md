# Visualization——用户手册

## 编译与运行

```bash
cd v6_fit_visualization
make configure              # 每台机器首次使用时执行一次
make visualization
./Visualization/eiid_plotter Visualization/config/plot_config.json
# 或者在根目录直接：make run-visualization
```

也可在 `Visualization/` 内运行 `make` 和 `./eiid_plotter config/plot_config.json`。ROOT 使用 batch 模式，不需要 X11。

## `plot_config.json`

| 参数 | 含义 |
|---|---|
| `input_root_file` | 重建生成的 `result.root` |
| `input_tree_name` | 结果 Tree，通常为 `EiidImage` |
| `output_directory` | PNG 和拟合摘要的输出目录 |
| `truth_info_file` | 独立真值 JSON |
| `draw_skymap` | 生成 `skymap.png` |
| `draw_spectrum` | 生成 `spectrum.png` |
| `draw_containment` | 生成 `containment.png` |
| `draw_energy_fit` | 生成 `energy_fit.png` |
| `draw_direction_fit` | 生成 `direction_fit.png` |
| `draw_energy_angle_map` | 生成 `energy_angle_map.png` |
| `write_fit_summary` | 生成机器可读的 `fit_summary.json` |
| `show_truth_markers` | 在图片中显示真值参考；不参与找峰或拟合 |

### `fit` 参数

| 参数 | 含义 | 默认值 |
|---|---|---|
| `energy_fit_half_width_MeV` | 以数据最高峰为中心的能量拟合半宽 | `0.16` |
| `direction_energy_gate_sigma` | 方向拟合使用的能量门宽，为初步能量拟合的 ±Nσ | `2.0` |
| `direction_fit_radius_degree` | 从方向图自身最高像素向外选取的局部拟合半径 | `30.0` |
| `direction_spectrum_radius_degree` | 最终能谱对拟合方向采用的圆形方向门半径 | `15.0` |

拟合半径越大，包含的背景越多；太小则可能截断峰。比较两次结果时应保持这些参数相同。

V5 的旧绘图配置也能直接使用：缺少上述新开关时默认不生成新图，缺少 `fit` 时采用表中的默认值。

## `truth_info.json`

| 参数 | 含义 |
|---|---|
| `theta_degree` | 真实源极角，单位度 |
| `phi_degree` | 真实源方位角，单位度 |
| `energy_MeV` | 真实源能量，单位 MeV |

真值只用于 bias、包含率与标记。修改真值不会改变程序从重建图中找到的拟合峰。

## 新增结果的阅读方法

- `energy_fit.png`：看 `mu_E` 与真值的偏差、`sigma_E`、相对 FWHM，以及下方残差是否存在明显非高斯结构。
- `direction_fit.png`：看拟合方向与真值的球面夹角、长短轴 σ；出现 `under-resolved` 警告时，不能把小于像素尺度的宽度解释为真实角分辨率。
- `energy_angle_map.png`：检查错误能量是否集中在较大角距离，以及能量和方向误差是否相关。
- `fit_summary.json`：适合脚本批量比较不同 Nside、迭代次数和事件数。

这些 Gaussian 宽度是重建图的描述性质量指标，不是独立事件统计意义下的严格误差棒。正式评价时应与 R50/R68/R90 一起报告。
