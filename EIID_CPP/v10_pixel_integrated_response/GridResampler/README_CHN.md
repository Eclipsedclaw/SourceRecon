# GridResampler——开发者说明

```text
GridResampler/
├── config/   Master/Target 网格和策略
├── include/  配置、IO、策略接口、Adapter
├── src/      nearest/polygon 与入口
├── Makefile
├── README.md / README_CHN.md
└── MANUAL.md / MANUAL_CHN.md
```

GridResampler 把 Master 方向—能量网格上的绝对效率转换到 Target 网格。它既能独立运行，也采用可替换的插值策略架构。

## 文件职责

- `ResamplerConfig`：读取 JSON，并验证 Master/Target 网格。
- `IInterpolationStrategy`：插值算法插件接口。
- `NearestInterpolation`：方向使用最近 HEALPix 像素中心，能量使用最近采样点。
- `PolygonInterpolation`：通过等面积公共细分估计球面重叠，并在能量轴上线性插值。
- `GridAdapter`：持有 Master 和 Target 网格，并创建配置指定的策略。
- `ResamplerIO`：严格读取和写入效率格式，同时保留源半径与效率定义。
- `resampler_main.cpp`：独立组合入口。
- `Makefile`：生成 `grid_resampler`，必要时自动编译 `common`。

## polygon 方法

Master 与 Target 像素会投影到更细的公共 HEALPix 网格。微像素均为等面积，因此落入某个 Master—Target 像素组合的微像素数量可近似两者的球面交叠面积。`polygon_subdivision_factor` 越大，共同网格越细，精度和计算成本也越高。

算法对 Target 像素覆盖范围内的效率场取面积平均，而不是把效率相加，因为每个输出值仍然是概率。

## 插件规则

新增插值算法时实现 `IInterpolationStrategy::resample`，并仅在 `GridAdapter` 中注册。ROOT I/O 和 `main.cpp` 不需要修改。

独立 Makefile 从 `../config/local.mk` 读取 ROOT、HEALPix、JSON 和 rpath 配置，该文件由根目录 `make configure` 一次生成。
