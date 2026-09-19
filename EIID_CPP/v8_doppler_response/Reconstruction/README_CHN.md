# Reconstruction——开发者说明

```text
Reconstruction/
├── config/   固定高斯、Voigt、双高斯配置
├── include/  配置、IO 和求解器接口
├── src/      EIID、LM-MLEM、配置与入口
├── io/       ROOT 事件/效率读取和图像写出
├── tests/    效率加权 MLEM 测试
├── Makefile
├── README.md / README_CHN.md
└── MANUAL.md / MANUAL_CHN.md
```

该模块把紧凑 ROOT 事件、HEALPix 网格、绝对探测效率、可插拔响应核和 LM-MLEM 求解器组装起来，可独立编译为 `EIID_Recon_V8`。

## 文件职责

- `include/ReconConfig.h`、`src/ReconConfig.cpp`：读取并验证 JSON；相对路径以配置文件所在目录为基准。
- `include/IReconstructionSolver.h`：重建求解器插件接口。
- `include/LmMlemSolver.h`、`src/LmMlemSolver.cpp`：列表模式乘法迭代，并对 `s_j > 0` 做显式保护。
- `include/EiidResponse.h`、`src/EiidResponse.cpp`：计算 ARM 查询并调用注入的 `IResponseKernel`。
- `include/RootEventReader.h`、`io/RootEventReader.cpp`：只读取已经精简的宏观事件。
- `include/RootEfficiencyReader.h`、`io/RootEfficiencyReader.cpp`：读取最小效率 Tree，并严格核对物理及网格元数据。
- `include/RootImageWriter.h`、`io/RootImageWriter.cpp`：写出包含物理坐标的自解释重建结果。
- `src/main.cpp`：组合入口；不在入口函数中隐藏物理公式。
- `config/recon_*.json`：固定高斯、Voigt 和双高斯运行参数。
- `Makefile`：独立编译配置。

## 求解器接口

`LmMlemSolver` 只依赖 `IGrid`、`AbsoluteEfficiencyMap` 和 `ReconConfig`，不会自行打开 ROOT 文件。新算法只需实现 `IReconstructionSolver`，再在 `main.cpp` 中完成注入，无需修改 I/O 类。

`EiidResponse` 构造 ARM 查询并交给注入的响应核得到 `q_ij`。V8 构造完整系统响应

\[
a_{ij}=\varepsilon_j q_{ij},
\qquad
\mu_i=\sum_j a_{ij}\lambda_j,
\]

再执行 LM-MLEM 更新。这样绝对效率真正参与事件的正向预测，而不是只在迭代末尾作为除数。效率 `ε_j <= 0` 的域外单元初值为零、迭代中保持为零。

## 输入保证

若 Nside、排序、方向数、能量数或范围不匹配，或者缺少源半径、效率定义不是当前的“4π 各向同性点源绝对探测效率 + Jeffreys 正则化”，`RootEfficiencyReader` 会直接报错。重复索引、缺失索引、越界索引和非法效率值由 `AbsoluteEfficiencyMap` 拒绝。

独立 Makefile 从 `../config/local.mk` 读取当前机器的 ROOT、HEALPix、JSON 和 rpath 配置；首次使用时在项目根目录执行 `make configure` 生成该文件。
