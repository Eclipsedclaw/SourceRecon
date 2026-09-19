# Visualization——开发者说明

```text
Visualization/
├── config/   绘图开关、真值和分析参数
├── include/  IPlotter、数据、分析与各 Plotter
├── src/      ROOT 绘图、质量分析和入口
├── config/   含四组像素积分对照的 plot_*.json
├── Makefile
├── README.md / README_CHN.md
└── MANUAL.md / MANUAL_CHN.md
```

Visualization 是独立的 ROOT 程序，只读取结果 ROOT 和真值 JSON。V10 用四份独立配置查看中心 Nside 8、积分 16->32、积分 32->64 i10 和 i20。默认输出集中到 `runs/latest/visualization/<configuration>/`。

## 组件

- `IPlotter`：所有绘图插件的多态接口。
- `VisConfig`：读取路径、开关、分析参数和真值。
- `ReconstructionDataReader`：只读一次 ROOT Tree，结果由各插件共享。
- `QualityAnalyzer`：统一计算能量峰、直接 FWHM、最短强度区间、方向质心、协方差椭圆和包含率。
- `EnergyMetricsPlotter`：能谱、半高交点、最短强度区间和累计强度。
- `DirectionMetricsPlotter`：局部球面切平面、加权质心及 1/2 RMS 椭圆。
- `EnergyAnglePlotter`：能量—真值角距离联合分布。
- `QualitySummaryWriter`：输出 `quality_summary.json`。
- `SkymapPlotter`、`SpectrumPlotter`、`ContainmentPlotter`：保留原有物理图。
- `vis_main.cpp`：组合根；只计算一次 `QualityAnalysisResult`，再以只读 `shared_ptr` 交给启用的插件。

## 分析顺序

```text
全方向能谱
  -> 三点抛物线细化数据峰位置
  -> 基线修正后的半高交点直接计算 FWHM
  -> 寻找包含指定强度比例的最短连续能量区间
  -> 用该能量区间筛选方向图
  -> 在方向图数据峰附近建立球面切平面
  -> 背景扣除后的加权质心与协方差特征值给出中心和 RMS 椭圆
  -> 以该质心为中心提取最终方向门控能谱
```

Gaussian 拟合是可关闭的诊断插件。拟合失败只记录状态，不会用矩估计伪装成拟合结果，也不影响上述主指标。

## 解释限制

MLEM 图像权重彼此相关，不是独立泊松计数。因此这些宽度是重建图的描述性质量指标，而不是严格置信区间。若方向短轴 RMS 小于 HEALPix 平均像素尺度，结果标记为 `under_resolved`。

新增图时实现 `IPlotter`，把 `.cpp` 放入 `src/`，再在 `vis_main.cpp` 注册。通配符 Makefile 会自动编译。
