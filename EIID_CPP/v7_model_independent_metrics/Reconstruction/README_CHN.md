# Reconstruction——开发者说明

该模块把紧凑 ROOT 事件、HEALPix 网格、绝对探测效率、EIID 响应函数和 LM-MLEM 求解器组装起来，可独立编译为 `EIID_Recon_V7`。

## 文件职责

- `include/ReconConfig.h`、`src/ReconConfig.cpp`：读取并验证 JSON；相对路径以配置文件所在目录为基准。
- `include/IReconstructionSolver.h`：重建求解器插件接口。
- `include/LmMlemSolver.h`、`src/LmMlemSolver.cpp`：列表模式乘法迭代，并对 `s_j > 0` 做显式保护。
- `include/EiidResponse.h`、`src/EiidResponse.cpp`：计算康普顿能量角与几何角的一致性响应。
- `include/RootEventReader.h`、`io/RootEventReader.cpp`：只读取已经精简的宏观事件。
- `include/RootEfficiencyReader.h`、`io/RootEfficiencyReader.cpp`：读取最小效率 Tree，并严格核对物理及网格元数据。
- `include/RootImageWriter.h`、`io/RootImageWriter.cpp`：写出包含物理坐标的自解释重建结果。
- `src/main.cpp`：组合入口；不在入口函数中隐藏物理公式。
- `config/recon_config.json`：运行时参数。
- `Makefile`：独立编译配置。

## 求解器接口

`LmMlemSolver` 只依赖 `IGrid`、`AbsoluteEfficiencyMap` 和 `ReconConfig`，不会自行打开 ROOT 文件。新算法只需实现 `IReconstructionSolver`，再在 `main.cpp` 中完成注入，无需修改 I/O 类。

`EiidResponse` 给出条件事件响应 `q_ij`。V7 先构造完整系统响应

\[
a_{ij}=\varepsilon_j q_{ij},
\qquad
\mu_i=\sum_j a_{ij}\lambda_j,
\]

再执行 LM-MLEM 更新。这样绝对效率真正参与事件的正向预测，而不是只在迭代末尾作为除数。效率 `ε_j <= 0` 的域外单元初值为零、迭代中保持为零。

## 输入保证

若 Nside、排序、方向数、能量数或范围不匹配，或者缺少源半径、效率定义不属于 V7，`RootEfficiencyReader` 会直接报错。重复索引、缺失索引、越界索引和非法效率值由 `AbsoluteEfficiencyMap` 拒绝。

独立 Makefile 从 `../config/local.mk` 读取当前机器的 ROOT、HEALPix、JSON 和 rpath 配置；首次使用时在项目根目录执行 `make configure` 生成该文件。
