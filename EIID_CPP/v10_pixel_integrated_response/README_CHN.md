# EIID V10 像素积分响应——开发者说明

V10 从 V9 独立复制而来，V9 未被修改。本版只解决一个明确问题：系统响应不再只在 HEALPix 像素中心取值，而可在像素内部的等面积子像素中心求平均。这样提高响应积分精度时，不必把每个子像素都变成新的 MLEM 未知量。

## 总体结构

```text
v10_pixel_integrated_response/
├── common/                  公共类型、HEALPix 网格、绝对效率容器
├── PixelIntegration/        【新增】像素方向采样与子像素缓存
├── SimulationSupport/       标定样本的公共 ROOT schema
├── Geant4_Simulation/       绝对效率 Master 图与可选精简事件模拟
├── GridResampler/           Master 效率图到 Nside 8/16/32 的转换
├── DopplerSampleGenerator/  Livermore/free 响应标定样本
├── ResponseCalibration/     Voigt、双高斯、Gaussian+Lorentzian 标定
├── ResponseKernel/          可插拔 ARM 概率密度
├── Reconstruction/         系统响应工厂、LM-MLEM 与 ROOT I/O
├── KernelBenchmark/         四组像素积分配置的统一质量比较
├── Visualization/           独立 ROOT 绘图与质量指标
├── Translator/              可选的 Step 级 ROOT -> 精简事件 ETL
├── scripts/prepare_run.sh   归档旧 runs/latest 并快照配置
├── config/local.mk          make configure 生成；不应跨机器复制
├── events.root              【外部输入；完整流程只读】
├── Makefile                 总编译与总工作流入口
├── README*.md               面向开发者
└── MANUAL*.md               面向使用者
```

## 数据流与模块边界

```text
Geant4_Simulation --absolute_efficiency_master.root-->
    GridResampler --absolute_efficiency_nside{8,16,32}.root--┐
                                                            │
DopplerSampleGenerator --> ResponseCalibration              │
    --> doppler_response.root --> ResponseKernel ------------┤
                                                            v
外部 events.root --> Reconstruction + PixelIntegration --> 四份 result ROOT
                                                            |
                         KernelBenchmark <-------------------+
                         Visualization  <--------------------+
```

`Translator` 是可选工具，不在默认 `make experiment` 中。其默认输出为 `translated_events.root`，避免覆盖外部 `events.root`。

## V10 的核心公式

V9 在父像素中心方向 \(\hat n_j\) 计算条件响应：

\[
q_{ij}=K\!\left(\theta_{\mathrm{geo}}(i,\hat n_j)-
\theta_{\mathrm{energy}}(i,E_j)\right).
\]

V10 的子像素模式把父像素细分为 \(M\) 个等面积 HEALPix 子像素，并采用它们的中心方向：

\[
\bar q_{ij}=\frac{1}{M}\sum_{k=1}^{M}
K\!\left(\theta_{\mathrm{geo}}(i,\hat n_{jk})-
\theta_{\mathrm{energy}}(i,E_j)\right).
\]

完整系统响应仍为

\[
a_{ij}=\varepsilon_j\bar q_{ij},
\]

因此绝对效率 \(\varepsilon_j\) 与像素内条件响应平均保持不同职责。默认 `Nside 32 -> 64` 时 \(M=(64/32)^2=4\)。未知量仍只有 Nside 32 的父像素数，并没有变成 Nside 64 重建。

## 新增类及职责

```text
IPixelDirectionSampler
├── PixelCenterSampler             一个父像素一个中心点；V9 对照
└── HealpixSubpixelSampler         等面积子像素中心
      └── SubpixelDirectionCache   RING 父像素 -> NESTED 子像素，预计算一次

ISystemResponseEvaluator
├── PointSystemResponseEvaluator
└── PixelIntegratedResponseEvaluator
          ^
          |
   SystemResponseFactory <--- ReconConfig.pixel_integration
```

`LmMlemSolver` 只依赖 `ISystemResponseEvaluator`，不知道采样器和响应核的具体类型。新增积分规则时，实现 `IPixelDirectionSampler`；新增系统响应组合方式时，实现 `ISystemResponseEvaluator`。两者都不要求修改 MLEM 循环。

## 索引与 HEALPix 约定

- 外部网格、ROOT 和 `Cell::directionIndex` 使用 `RING`。
- 子像素层级映射内部使用 `NESTED`，因为同一父像素的后代连续排列。
- 展平单元索引固定为 `direction_index * energy_count + energy_index`。
- `healpix_nside` 与 `integration_nside` 必须为 2 的整数幂。
- `integration_nside / healpix_nside` 必须为 2 的整数幂。
- 每父像素采样数为 `(integration_nside / healpix_nside)^2`。

## 四组受控比较

| 配置 | 父网格 | 积分网格 | 采样/父像素 | 迭代 |
|---|---:|---:|---:|---:|
| `recon_center_nside8_i10.json` | 8 | 8 | 1 | 10 |
| `recon_integrated_nside16_32_i10.json` | 16 | 32 | 4 | 10 |
| `recon_integrated_nside32_64_i10.json` | 32 | 64 | 4 | 10 |
| `recon_integrated_nside32_64_i20.json` | 32 | 64 | 4 | 20 |

前三组观察空间离散与像素积分；后两组只改变迭代次数。默认 `recon_config.json` 指向 Nside 32 -> 64、10 次迭代。20 次不是默认值，防止把迭代噪声误认为分辨率提升。

## 计算量

当前列表模式实现的主导计算量近似为

\[
T\approx C\,N_{\mathrm{iter}}N_{\mathrm{event}}
(12N_{\mathrm{side}}^2)N_E M,
\]

其中 \(M\) 是每父像素采样数。子像素积分提高每个单元的响应精度，但不会减少事件数或父网格单元数。高分辨率配置是正式计算，不是快速 smoke test。

## 自检层次

- `PixelIntegration/tests/test_pixel_sampling.cpp`：中心等价、父子映射、全天下等面积对称性。
- `Reconstruction/tests/test_efficiency_weighted_mlem.cpp`：验证 `a_ij=ε_j q_ij` 与末端效率归一化的一致性。
- 各模块 `make test`：模块内部契约。
- 根目录 `make test`：统一单元测试。
- `make validate-events`：昂贵计算前只读校验外部事件文件。

依赖与操作命令见 [MANUAL_CHN.md](MANUAL_CHN.md)。
