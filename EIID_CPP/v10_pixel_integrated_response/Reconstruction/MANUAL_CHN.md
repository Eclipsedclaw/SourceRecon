# Reconstruction——用户手册

```bash
cd v10_pixel_integrated_response
make configure
make reconstruction
./Reconstruction/EIID_Recon_V10 Reconstruction/config/recon_config.json
```

只验证外部事件：

```bash
./Reconstruction/EIID_Recon_V10 --validate-events-only \
    Reconstruction/config/recon_center_nside8_i10.json
```

## 配置

| 参数 | 含义 |
|---|---|
| `input_events_file/tree` | 输入事件 ROOT 和 Tree |
| `output_result_file/tree` | 输出图像 ROOT 和 Tree |
| `absolute_efficiency_file/tree` | 与父网格一致的绝对效率 |
| `healpix_nside` | 重建未知量的方向 Nside |
| `healpix_ordering` | 必须为 `RING` |
| `energy_min_MeV/max_MeV` | 候选入射能量范围 |
| `energy_point_count` | 能量格点数 |
| `iteration_count` | LM-MLEM 迭代次数 |
| `response_kernel.*` | 核类型、标定 ROOT、Tree/直方图名和后备 sigma |
| `pixel_integration.strategy` | `pixel_center` 或 `healpix_subpixel` |
| `pixel_integration.integration_nside` | 子像素积分 Nside |
| `denominator_floor` | 除法和零向量的数值保护 |
| `event_branches/result_branches/absolute_efficiency_branches` | ROOT Branch 映射 |

四组正式命令可在根目录运行：`make reconstruct-center`、`make reconstruct-integrated-16`、`make reconstruct-integrated-32`、`make reconstruct-iteration-20`。输出统一位于 `runs/latest/reconstruction/`。

`recon_config.json` 是推荐默认值：父 Nside 32、积分 Nside 64、10 次迭代。提高 `iteration_count` 不等同于提高空间离散精度，应使用 i10/i20 对照判断。
