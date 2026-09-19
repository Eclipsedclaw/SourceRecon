# GridResampler——用户手册

## 编译与运行

新机器先在 V7 根目录运行一次 `make configure`。此后本模块可以独立编译：

```bash
cd GridResampler
make
./grid_resampler config/resampler_config.json
```

## 可调参数

| 参数 | 含义 |
|---|---|
| `input_absolute_efficiency_file` | Master 绝对效率 ROOT 文件 |
| `input_absolute_efficiency_tree` | Master Tree 名称 |
| `output_absolute_efficiency_file` | Target 绝对效率 ROOT 文件 |
| `output_absolute_efficiency_tree` | Target Tree 名称 |
| `master_grid.healpix_nside` | Geant4 Mode 0 使用的 Nside |
| `master_grid.energy_min_MeV` | Master 能量下限 |
| `master_grid.energy_max_MeV` | Master 能量上限 |
| `master_grid.energy_point_count` | Master 能量点数 |
| `target_grid.healpix_nside` | Reconstruction 要求的 Nside |
| `target_grid.energy_min_MeV` | Target 能量下限 |
| `target_grid.energy_max_MeV` | Target 能量上限 |
| `target_grid.energy_point_count` | Target 能量点数 |
| `interpolation` | `nearest` 或 `polygon` |
| `polygon_subdivision_factor` | polygon 模式的精度/耗时倍率 |
| `require_full_coverage` | 若 Target 像素没有任何覆盖，是否立即报错 |

快速检查可使用 `nearest`；正式转换建议使用 `polygon`，并逐渐增大 `polygon_subdivision_factor`，直至结果基本稳定。

Target 能量范围必须包含在 Master 范围内。程序会自动保留 `source_radius_mm`，不能把不同源半径生成的效率图混合使用。
