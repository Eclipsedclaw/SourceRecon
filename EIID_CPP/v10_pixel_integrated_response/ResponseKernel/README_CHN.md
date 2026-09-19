# ResponseKernel——开发者说明

```text
ResponseKernel/
├── include/
│   ├── IResponseKernel.h
│   ├── ResponseQuery.h
│   ├── KernelParameterTable.h
│   ├── FixedGaussianKernel.h
│   ├── VoigtKernel.h
│   ├── DoubleGaussianKernel.h
│   ├── GaussianLorentzianMixtureKernel.h
│   ├── HistogramKernel.h
│   ├── RootKernelReader.h
│   └── ResponseKernelFactory.h
├── src/                          各响应核、插值和工厂
├── io/RootKernelReader.cpp       ROOT 参数/PDF 读取
├── tests/                        插值与归一化测试
├── Makefile
├── README.md / README_CHN.md
└── MANUAL.md / MANUAL_CHN.md
```

所有响应核通过 `IResponseKernel::evaluate()` 返回单位为 `degree^-1` 的归一化 ARM 概率密度。标定参数存入连续一维向量，热循环查询采用能量—散射角双线性插值，越界查询夹到标定边界。

`GaussianLorentzianMixtureKernel` 实现独立宽度的

\[
p(x)=(1-\eta)G(x;\mu,\sigma)+\eta L(x;\mu,\Gamma).
\]

它与 Voigt 的“卷积”不同，是两个归一化分量的加权和。工厂加载标定模型时还会检查相应的 `*_converged` Branch，防止失败拟合进入 MLEM。

增加响应模型只需实现接口并在 `ResponseKernelFactory` 注册，不应修改 `EiidResponse` 或求解器。
