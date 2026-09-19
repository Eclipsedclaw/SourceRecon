# Visualization——开发者说明

Visualization 是独立的 ROOT 绘图程序，只依赖重建结果格式，不依赖模拟器或 LM-MLEM 的具体实现。

## 文件职责

- `iplotter.h`：多态绘图插件接口。
- `vis_config.h/.cpp`：读取绘图 JSON 和真值 JSON。
- `reconstruction_data.h/.cpp`：一次性读取 `result.root`，供所有 Plotter 共用。
- `skymap_plotter.h/.cpp`：全天球热力图，相机正前方 `-Z` 位于图像中心。
- `spectrum_plotter.h/.cpp`：在方向维度求和后的能谱。
- `containment_plotter.h/.cpp`：方向累计包含率及 R50/R68/R90。
- `plot_utils.h/.cpp`：共用坐标变换与分组工具。
- `vis_main.cpp`：根据配置开关，通过 `IPlotter` 指针构造所需 Plotter。

新增图片时，实现 `IPlotter`，把源码放入 `src/`，再在 `vis_main.cpp` 中注册。Makefile 使用通配符，会自动编译新的 `.cpp` 文件。

独立 Makefile 从 `../config/local.mk` 读取 ROOT、JSON 和 rpath 配置，该文件由根目录 `make configure` 一次生成。
