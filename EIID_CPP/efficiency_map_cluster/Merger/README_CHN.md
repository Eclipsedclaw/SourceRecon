# Merger：开发说明

只依赖ROOT和common，不依赖Geant4/HEALPix，可独立编译部署。

```text
Merger/
├── include/CountMerger.h
├── src/CountMerger.cpp
├── src/main.cpp
└── CMakeLists.txt
```

CountMerger依照manifest读取所有预期分块，检查配置/软件/编号/事件覆盖后累加64位整数。临时文件不参与；意外多出的.root会报错。允许合理的原始零计数。

最终只计算一次efficiency=(总valid/总emitted)*cone_fraction，不能简单平均不同统计量分块的efficiency。最终RawEfficiency覆盖完整天空索引，并写元数据供Quicklook独立画图。

写入由common的RootCountsIO承担。已存在最终文件时逐行验证而不覆盖。main提供正常合并与--check-only模式。上游是Simulation分块；下游是小服务器Quicklook，而非新的绘图模块。

