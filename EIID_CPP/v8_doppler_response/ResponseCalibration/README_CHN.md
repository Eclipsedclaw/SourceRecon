# ResponseCalibration——开发者说明

## 定位与目录

```text
ResponseCalibration/
├── config/calibration_config.json
├── include/
│   ├── CalibrationConfig.h
│   ├── ResponseSample.h
│   ├── RootSampleReader.h
│   ├── IResponseFitter.h
│   ├── VoigtFitter.h
│   ├── DoubleGaussianFitter.h
│   └── CalibrationPipeline.h
├── src/                           配置、拟合、流水线和入口
├── io/RootSampleReader.cpp
├── output/model_comparison.json  运行生成
├── figures/                      单分箱拟合图
├── Makefile
├── README.md / README_CHN.md
└── MANUAL.md / MANUAL_CHN.md
```

流水线按能量和散射角分箱，通过 eventID 哈希稳定拆分训练/测试集。两个 `IResponseFitter` 使用同一训练直方图；训练似然产生 AIC/BIC，测试集产生 held-out NLL。输出参数表同时含两套参数，避免两个模型使用不同分箱。

默认配置只使用一个 `[0,180]` 散射角区间，因为当前低统计 ch2→ch1 样本不支持独立标定后向分箱。参数表的角度轴和插值接口仍保留，未来可在高统计样本上细分。稀疏 ARM 直方图使用 Poisson binned likelihood 拟合，而不是默认卡方拟合。

经验 `TH3D` 的每个能量—角度切片按 ARM bin 宽归一化为概率密度。
