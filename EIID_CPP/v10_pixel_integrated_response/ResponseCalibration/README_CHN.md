# ResponseCalibration——开发者说明

## 模块定位

该模块把 DopplerSampleGenerator 产生的 Livermore 标定样本，按入射能量和真实散射角分箱，并在完全相同的训练/测试数据上拟合三种可插拔 ARM 响应：

- `VoigtFitter`：高斯与洛伦兹卷积；
- `DoubleGaussianFitter`：窄核心与宽尾的双高斯混合；
- `GaussianLorentzianMixtureFitter`：独立宽度的高斯与洛伦兹加权和。

```text
ResponseCalibration/
├── config/calibration_config.json
├── include/
│   ├── IResponseFitter.h
│   ├── VoigtFitter.h
│   ├── DoubleGaussianFitter.h
│   ├── GaussianLorentzianMixtureFitter.h
│   ├── CalibrationConfig.h
│   └── CalibrationPipeline.h
├── src/                         三种拟合器、流水线与入口
├── io/RootSampleReader.cpp      只读标定样本
├── Makefile
├── README.md / README_CHN.md
└── MANUAL.md / MANUAL_CHN.md
```

## 数据与判断逻辑

流水线使用 `eventID` 的稳定哈希拆分训练集和测试集。训练集给出 Poisson 似然、AIC、BIC；测试集给出 held-out NLL。每次拟合同时保存 ROOT 状态码、协方差状态、EDM 和函数调用数，不能仅凭“画出来像”判断收敛。

三个模型使用同一分箱、同一直方图和同一测试集。输出 `doppler_response.root` 保存全部参数；`model_comparison.json` 保存逐分箱指标；`model_status.json` 汇总模型是否可用于重建。只有一个模型在所有必需分箱均收敛时，其 `usable` 才为 `true`。

默认只使用 `[0°,180°]` 的单个散射角区间，因为当前统计不足以可靠标定更细的角度依赖。ROOT 中保留角度区间中心、下界和上界，避免把区间中心误当成每个事件的真实散射角。

增加新模型时，只需实现 `IResponseFitter`、在 `CalibrationPipeline` 注册输出字段，并在 ResponseKernel 注册对应运行时核；不应修改 MLEM。
