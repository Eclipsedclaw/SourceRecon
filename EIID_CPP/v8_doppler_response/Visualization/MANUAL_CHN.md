# Visualization——中文用户手册

```text
Visualization/{config,include,src,figures} -> eiid_plotter
```

## 编译与运行

```bash
cd v8_doppler_response
make configure                 # 每台机器首次使用执行一次
make visualization
make run-visualization
```

也可直接运行：

```bash
./Visualization/eiid_plotter Visualization/config/plot_config.json
```

ROOT 使用 batch 模式，不需要 X11。

## `plot_config.json`

| 参数 | 含义 |
|---|---|
| `input_root_file` | 重建输出 `result.root` |
| `input_tree_name` | 通常为 `EiidImage` |
| `output_directory` | PNG 和 JSON 输出目录 |
| `truth_info_file` | 真值 JSON |
| `draw_skymap` | 生成 `skymap.png` |
| `draw_spectrum` | 生成 `spectrum.png` |
| `draw_containment` | 生成 `containment.png` |
| `draw_energy_metrics` | 生成 `energy_resolution.png` |
| `draw_direction_metrics` | 生成 `direction_resolution.png` |
| `draw_energy_angle_map` | 生成 `energy_angle_map.png` |
| `write_quality_summary` | 生成 `quality_summary.json` |
| `show_truth_markers` | 显示真值参考；不参与找峰 |

### `analysis`

| 参数 | 含义 | 默认值 |
|---|---|---|
| `energy_interval_fraction` | 最短连续能量区间需包含的强度比例 | `0.68` |
| `gaussian_fit_enabled` | 是否额外尝试 Gaussian 诊断拟合 | `true` |
| `gaussian_fit_half_width_MeV` | 可选能量拟合窗口半宽 | `0.16` |
| `direction_local_radius_degree` | 方向质心/协方差的局部窗口半径 | `30.0` |
| `direction_spectrum_radius_degree` | 最终能谱的圆形方向门半径 | `15.0` |

V6 的 `draw_energy_fit`、`draw_direction_fit`、`write_fit_summary` 和 `fit` 配置仍能读取，但建议使用 V7 新名字。

## 结果怎么读

- `energy_resolution.png`：主结果是 `E_peak`、直接 FWHM、`FWHM/E_peak` 和最短 68% 强度区间。相对 FWHM 用于跨能量比较；绝对 FWHM 会同时显示。
- `direction_resolution.png`：主结果是数据加权质心、角偏差、长短轴 RMS 和 HEALPix 像素尺度。
- `containment.png`：读取 R50、R68、R90；它对非 Gaussian 尾部更稳健。
- `energy_angle_map.png`：检查方向误差与能量误差是否相关。
- `quality_summary.json`：保存全部数值和警告，适合批量比较。

`optional Gaussian: unavailable` 只表示 Gaussian 模型不适合或 ROOT 未收敛，不表示主指标失败。
