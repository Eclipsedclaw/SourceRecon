# EIID V9 响应模型实验版——开发者说明

V9 是从 V8 派生的实验版本，用同一份外部 `events.root` 比较三种 ARM 响应模型：

1. `DoubleGaussianKernel`：两个同中心高斯的加权和；
2. `VoigtKernel`：高斯与洛伦兹的卷积；
3. `GaussianLorentzianMixtureKernel`：独立宽度的高斯与洛伦兹加权和。

V8 目录不被修改。V9 不把 `events.root` 当成生成物；它只校验并读取用户提供的文件。

## 总体结构

```text
v9_response_mixture_experiment/
├── common/                 HEALPix 网格、公共物理类型、绝对效率容器
├── Geant4_Simulation/      生成绝对探测效率主网格
├── GridResampler/          将效率主网格转换到重建网格
├── DopplerSampleGenerator/ 生成响应标定样本
├── SimulationSupport/      标定样本公共 schema
├── ResponseCalibration/    拟合三种模型并输出收敛状态
├── ResponseKernel/         可插拔响应核接口及三种实现
├── Reconstruction/         EIID/LM-MLEM 重建
├── KernelBenchmark/        只比较可用模型
├── Visualization/          为每个可用模型生成质量图
├── Translator/             可选的 Geant4 Step → Events 翻译器
├── scripts/prepare_run.sh  安全建立/归档统一运行目录
├── events.root             【外部输入，不由 V9 生成】
├── runs/latest/            当前实验的集中输出
└── Makefile                总编译与总工作流入口
```

## 数据流

```text
外部 events.root ──校验──────────────────────────────────────┐
                                                            │
Geant4 efficiency simulation → master efficiency            │
                                  ↓                         │
                           GridResampler                     │
                                  ↓                         │
                         target efficiency                   │
                                                            │
Doppler sample grid → ResponseCalibration                    │
                           ├─ Double Gaussian parameters      │
                           ├─ Voigt parameters + status       │
                           └─ Gaussian-Lorentzian parameters  │
                                  ↓                         │
                         model_status.json                    │
                                  ↓                         │
外部 events.root + efficiency + 每个可用 Kernel → Reconstruction
                                  ↓
                        Benchmark + Visualization
```

## 关键设计

所有响应核实现 `IResponseKernel`，由 `ResponseKernelFactory` 按 JSON 中的 `type` 创建。重建算法只依赖接口，不依赖具体拟合函数。

Gaussian–Lorentzian mixture 使用

\[
p(x)=(1-\eta)G(x;\mu,\sigma)+\eta L(x;\mu,\Gamma),
\]

其中两部分宽度独立。它描述“核心事件群＋长尾事件群”，不是 Voigt 卷积的数值近似。

`ResponseCalibration` 为每个能量/角度 bin 保存 ROOT fit status、covariance status、EDM、function calls 和收敛标记。一个模型只有在全部必要 bin 收敛时才标记为 `usable=true`。未收敛模型保留诊断，但不进入重建、Benchmark 或绘图；禁止在部分 bin 中偷偷回退到另一模型。

`KernelBenchmark` 在同一份留出标定样本上汇总 test NLL、AIC 和 BIC，同时比较最终重建的峰值角误差、峰值能量误差、能谱宽度及 R50/R68/R90。程序保留这些不同物理意义的指标，不把它们任意揉成一个总分；若 Voigt 未通过收敛门禁，它会被明确记录为跳过，而不是用旧文件或其他模型代替。

`make experiment` 调用 `scripts/prepare_run.sh`。已有 `runs/latest/` 会移动到带时间戳的 `runs/archive/`，不会被删除。当前配置副本和外部事件文件 SHA-256 写入新运行目录。

## 主要新增文件

```text
ResponseCalibration/include/GaussianLorentzianMixtureFitter.h
ResponseCalibration/src/GaussianLorentzianMixtureFitter.cpp
ResponseKernel/include/GaussianLorentzianMixtureKernel.h
ResponseKernel/src/GaussianLorentzianMixtureKernel.cpp
Reconstruction/config/recon_gaussian_lorentzian_mixture.json
Visualization/config/plot_gaussian_lorentzian_mixture.json
scripts/prepare_run.sh
```

每个模块均可独立编译；模块自己的 `README*.md` 面向开发者，`MANUAL*.md` 面向使用者。
