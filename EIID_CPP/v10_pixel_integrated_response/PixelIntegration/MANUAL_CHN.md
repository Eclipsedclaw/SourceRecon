# PixelIntegration——用户手册

本模块通常由 Reconstruction 自动编译，也可独立构建和测试：

```bash
cd v10_pixel_integrated_response
make configure
make -C PixelIntegration
make -C PixelIntegration test
```

输出为 `PixelIntegration/libpixel_integration.a`。它没有自己的 JSON；运行参数位于 Reconstruction 配置：

| 参数 | 含义 |
|---|---|
| `pixel_integration.strategy` | `pixel_center` 或 `healpix_subpixel` |
| `pixel_integration.integration_nside` | 用于响应积分的子像素 Nside |

规则：两个 Nside 都必须是 2 的整数幂；积分 Nside 不小于父 Nside；两者比值也必须是 2 的整数幂。`8 -> 8` 为 1 个中心样本；`16 -> 32` 和 `32 -> 64` 均为 4 个等面积样本。

清理：`make -C PixelIntegration clean`。
