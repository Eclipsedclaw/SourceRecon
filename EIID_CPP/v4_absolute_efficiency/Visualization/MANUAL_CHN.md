# Visualization——用户手册

## 编译与运行

新机器先在 V4 根目录执行一次 `make configure`，以后直接运行：

```bash
cd Visualization
make
./eiid_plotter config/plot_config.json
```

## `plot_config.json`

| 参数 | 含义 |
|---|---|
| `input_root_file` | 重建生成的 `result.root` 路径 |
| `input_tree_name` | 结果 Tree 名，通常为 `EiidImage` |
| `output_directory` | PNG 图片输出目录 |
| `truth_info_file` | 真值 JSON 路径 |
| `draw_skymap` | 是否生成全天球热力图 |
| `draw_spectrum` | 是否生成能谱 |
| `draw_containment` | 是否生成方向累计包含率图 |
| `show_truth_markers` | 是否叠加真值方向标记和真值能量线 |

## `truth_info.json`

| 参数 | 含义 |
|---|---|
| `theta_degree` | 真实源极角，单位度 |
| `phi_degree` | 真实源方位角，单位度 |
| `energy_MeV` | 真实源能量 |

默认输出目录为 `Visualization/figures/`。ROOT 使用 batch 模式，因此无需 X11 图形转发。

方向包含半径不能解释到小于 HEALPix 像素尺度。图中会标明网格分辨率，避免把粗网格造成的 `R50 = 0°` 误认为无限角分辨率。
