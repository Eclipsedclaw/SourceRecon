# ResponseKernel——开发者说明

## 定位与目录

```text
ResponseKernel/
├── include/
│   ├── IResponseKernel.h          响应核多态接口
│   ├── ResponseQuery.h            ARM、能量、散射角查询对象
│   ├── KernelParameterTable.h     连续一维存储与双线性插值
│   ├── FixedGaussianKernel.h
│   ├── VoigtKernel.h
│   ├── DoubleGaussianKernel.h
│   ├── HistogramKernel.h
│   ├── RootKernelReader.h
│   └── ResponseKernelFactory.h
├── src/                            各响应核和工厂实现
├── io/RootKernelReader.cpp         ROOT 参数/PDF 读取
├── tests/                          插值与归一化测试
├── Makefile
├── README.md / README_CHN.md       开发者文档
└── MANUAL.md / MANUAL_CHN.md       用户手册
```

`evaluate()` 返回 `degree^-1` 的归一化密度。参数表必须是完整矩形；二维查询使用双线性插值，范围外夹到边界。ROOT 对象只在加载时存在，热循环中的经验 PDF 已复制到普通向量。

增加模型时实现 `IResponseKernel` 并在工厂注册，不应修改 MLEM。
