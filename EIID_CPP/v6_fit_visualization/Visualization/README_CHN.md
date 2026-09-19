# Visualization——开发者说明

Visualization 是独立的 ROOT 绘图程序，只读取 `result.root` 与真值 JSON，不依赖模拟器或 LM-MLEM 的内部实现。V6 在原有三张物理图之外，新增一套共享拟合分析和三张诊断图。

## 文件职责

- `iplotter.h`：所有绘图插件的多态接口。
- `vis_config.h/.cpp`：读取绘图、拟合窗口和真值配置。
- `reconstruction_data.h/.cpp`：一次读取 `result.root`，供所有插件共享。
- `plot_utils.h/.cpp`：坐标变换、HEALPix 分辨率和边缘化工具。
- `skymap_plotter.h/.cpp`：以相机正前方 `-Z` 为中心的全天球热力图。
- `spectrum_plotter.h/.cpp`：对方向求和后的原始能谱。
- `containment_plotter.h/.cpp`：R50、R68、R90 方向累计包含率。
- `fit_analysis.h/.cpp`：统一执行能量局部高斯拟合、切平面二维椭圆高斯拟合和包含率计算；不负责画图。
- `energy_fit_plotter.h/.cpp`：方向门控后的能谱、局部高斯和残差。
- `direction_fit_plotter.h/.cpp`：能量门控后的局部方向图、拟合中心和 1σ/2σ 椭圆。
- `energy_angle_plotter.h/.cpp`：能量与相对真值方向夹角的二维联合图。
- `fit_summary_writer.h/.cpp`：把拟合量写入 `fit_summary.json`。
- `vis_main.cpp`：组合根；只计算一次 `FitAnalysisResult`，再以只读 `shared_ptr` 交给各插件。

## 拟合流水线

```text
全方向能谱
  -> 在数据自身最高峰附近做 Gaussian + constant 拟合
  -> 用 fitted mean ± N sigma 选择能量
  -> 在能量门控天空图自身最高像素附近建立球面切平面
  -> 做二维椭圆 Gaussian + constant 拟合
  -> 以拟合方向为圆心重新提取能谱并给出最终能量拟合
```

找峰和确定拟合中心时不使用真值；真值只用于画参考标记和计算 bias。方向也不分别拟合 `theta` 与 `phi`，避免方位角周期边界和极点奇异性。

`FitAnalysisResult` 是普通 C++ 数据结构，因此绘图器只负责展示。新增图片时实现 `IPlotter`，源码放入 `src/`，再在 `vis_main.cpp` 注册；通配符 Makefile 会自动编译新 `.cpp`。

## 解释限制

MLEM 图像权重不是相互独立的泊松计数。因此当前 Gaussian 的中心和宽度是便于比较两次重建的描述量，不是严格置信区间。若 `sigma_minor` 小于平均 HEALPix 像素尺度，结果会被标记为 `under_resolved`。

独立 Makefile 从 `../config/local.mk` 读取 ROOT、JSON 和 rpath 配置；该文件由 V6 根目录 `make configure` 生成。
