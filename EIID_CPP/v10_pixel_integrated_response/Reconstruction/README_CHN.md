# Reconstruction——开发者说明

```text
Reconstruction/
├── config/                              四组 V10 对照配置及兼容配置
├── include/
│   ├── ReconConfig.h                    JSON 与 pixel_integration 配置
│   ├── IReconstructionSolver.h          求解器接口
│   ├── ISystemResponseEvaluator.h       系统条件响应接口
│   ├── PointSystemResponseEvaluator.h   像素中心实现
│   ├── PixelIntegratedResponseEvaluator.h 子像素平均实现
│   ├── SystemResponseFactory.h          按配置创建实现
│   ├── LmMlemSolver.h / EiidResponse.h
│   └── Root*Reader.h / RootImageWriter.h
├── src/                                 物理、求解器、工厂和入口
├── io/                                  ROOT I/O
├── tests/                               效率加权 MLEM 测试
├── Makefile                             生成 EIID_Recon_V10
├── README.md / README_CHN.md
└── MANUAL.md / MANUAL_CHN.md
```

`EiidResponse` 负责单个候选方向的康普顿运动学和 ARM 查询。`PixelIntegratedResponseEvaluator` 对采样器返回的方向逐一调用它并取平均。`LmMlemSolver` 只看到 `ISystemResponseEvaluator`，因此既不依赖具体响应核，也不依赖具体像素积分策略。

完整系统响应为

\[
a_{ij}=\varepsilon_j\bar q_{ij},\quad
\mu_i=\sum_j a_{ij}\lambda_j.
\]

效率参与正向预测；在 MLEM 末端再用同一 `ε_j` 做灵敏度归一化。`ε_j<=0` 的单元从初值开始即保持为零。条件响应平均不能把效率偷偷混入响应核。

`ReconConfig` 还负责在分配大数组前拒绝非法 Nside、非法细分比、非正迭代/数值阈值及不一致能量范围。旧配置缺少 `pixel_integration` 时默认采用 `pixel_center`，用于兼容和对照。
