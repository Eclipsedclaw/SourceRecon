# Efficiency Map Quick-look

这是一个临时、独立的 ROOT 绘图工具，用于展示效率图在指定能量处的方向切片。

它不会编译或修改 V10，也不会成为重建程序的一部分。

## 文件

```text
efficiency_map_quicklook/
├── plot_efficiency_map.C   # 读取、插值和绘图实现
├── run_efficiency_map.C    # 用户只需在这里填写输入参数
├── figures/                # 运行时自动创建
└── README_CHN.md
```

## 使用方法

先打开 `run_efficiency_map.C`，确认输入文件路径：

```cpp
const char* inputRootFile =
    "../v10_pixel_integrated_response/runs/latest/efficiency/absolute_efficiency_master.root";
```

然后在服务器上运行：

```bash
cd ~/labwork/SourceRecon/EIID_CPP/efficiency_map_quicklook
root -l -b -q run_efficiency_map.C
```

不需要执行 `make`。

成功后生成：

```text
figures/efficiency_map_E0p662_linear.png
figures/efficiency_map_E0p662_log.png
figures/efficiency_map_E0p662_skymap_aitoff_log.png
```

- `linear` 使用线性色标，适合观察最高效率区域。
- `log` 使用对数色标，适合观察跨数量级的低效率结构，通常更适合汇报展示。
- `skymap_aitoff_log` 是等面积 Hammer-Aitoff 全天球投影，适合以标准 skymap 形式展示。

## 0.662 MeV 如何取得

如果效率图的能量网格没有恰好包含 `0.662 MeV`，工具会自动在相邻两层之间做线性插值。

例如 `0.3--2.0 MeV`、共 50 个等间距格点时，使用：

```text
0.646939 MeV，权重 0.565882
0.681633 MeV，权重 0.434118
```

图片顶部和终端输出都会明确记录这两个能量层及其权重。

## 图中的坐标

- 图中心是相机正前方 `-Z`。
- 横轴是相机中心经度，纵轴是相机中心纬度。
- 当前 V10 只模拟前半球，因此两侧灰色区域表示“未模拟”，不表示物理效率为零。
- 颜色表示无量纲的绝对探测效率；不要再次乘以 HEALPix 像素立体角。

## 更换输入或能量

只需修改 `run_efficiency_map.C` 中的参数。例如：

```cpp
const double targetEnergyMeV = 1.0;
```

如果输入文件覆盖全天球，则修改：

```cpp
const bool frontHemisphereOnly = false;
```
