# Simulation：开发说明

独立可执行文件 efficiency_simulator，使用 Geant4 原生多线程。不混入重建、能谱拟合、可视化或事件ROOT转换。

```text
Simulation/
├── include/
│   ├── TaskRunner.hh / ActionInitialization.hh
│   ├── EfficiencyRun.hh / RunAction.hh / EventAction.hh
│   ├── PrimaryGeneratorAction.hh / SimulationGrid.hh
│   ├── ISourceGeometry.hh / IEmissionConePolicy.hh
│   ├── Ch2CenteredHemisphereSource.hh / AutoBoundingConePolicy.hh
│   └── DetectorGeometryInfo、DetectorConstruction、TrackerHit/SD、MyPhysicsList等
├── src/                       # 对应实现，含 main.cpp
└── CMakeLists.txt
```

- main 只解析 manifest路径和job_id，调用TaskRunner。
- TaskRunner 检查依赖数据集、冻结计划和已有分块；只为未完成块调用BeamOn。
- ActionInitialization 为每个worker创建动作；主线程只创建RunAction用于汇总。
- SimulationGrid 将全局事例号映射到HEALPix方向—能量cell，支持单cell跨块。
- PrimaryGeneratorAction 明确选择gamma；用全局事件编号设随机种子；缓存本线程上次cell的源位置与自动发射锥。
- EventAction 消费同事件的所有hits，分别累加ch2/ch1能量后触发；不要求光电全吸收。
- EfficiencyRun 是每线程计数表，Merge 安全相加。
- RunAction 只在master完成全部事件后计算立体角占比、校验、输出一个ROOT分块。
- ISourceGeometry/IEmissionConePolicy 是可替换点，既有实现不改变原试验的源几何/包络定义。
- DetectorConstruction/TrackerSD/MyPhysicsList 继承已修复原版物理。Geant4管理粒子枪以外的已注册Action/Run/几何对象生命周期。

只读几何/配置在线程间共享；hits、粒子枪与计数不共享。ROOT仅在master使用。请不要把进程静态可变计数器加入EventAction。

