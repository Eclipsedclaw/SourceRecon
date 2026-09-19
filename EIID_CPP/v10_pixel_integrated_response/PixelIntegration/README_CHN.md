# PixelIntegration——开发者说明

```text
PixelIntegration/
├── include/
│   ├── IPixelDirectionSampler.h       采样策略接口
│   ├── PixelCenterSampler.h           单中心点对照实现
│   ├── HealpixSubpixelSampler.h       HEALPix 等面积子像素实现
│   └── SubpixelDirectionCache.h       预计算方向缓存
├── src/                               上述实现
├── tests/test_pixel_sampling.cpp      父子映射与等价性测试
├── Makefile                           生成 libpixel_integration.a
├── README.md / README_CHN.md
└── MANUAL.md / MANUAL_CHN.md
```

该模块只回答“一个父像素内部在哪些方向计算响应”，不包含事件、能量公式、响应核、效率或 MLEM。

外部方向索引始终按 RING。`SubpixelDirectionCache` 先将父像素转为 NESTED 编号，再利用 HEALPix 层级关系找到连续的子像素编号，最后缓存子像素中心的 `Vec3`。MLEM 热循环只进行 O(1) span 查询，不重复创建向量。

若父 Nside 为 \(N_p\)，积分 Nside 为 \(N_s\)，每父像素样本数为：

\[
M=(N_s/N_p)^2.
\]

当前是等权平均，因为所有 HEALPix 子像素等面积。以后加入自适应求积时，应新增 `IPixelDirectionSampler` 实现，不修改现有采样器。
