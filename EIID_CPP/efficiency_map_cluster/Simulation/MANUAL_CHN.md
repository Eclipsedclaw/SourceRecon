# Simulation：操作说明

生成分块整数计数，不直接拼接重建结果、不生成events.root、不画图。

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

在整个项目根目录（environment.sh 仅为可选覆盖）：

```bash
make configure
make all
make prepare
make run-local
```

run-local最后会调用合并器，因此最初建议 make all；只想运行模拟某个作业：

```bash
python3 cluster/workflow.py job --manifest runs/smoke_001/manifest.json 0
```

0是job_id，不是eventID或线程号。cluster使用 make submit，不在登录节点执行上面的大规模模拟。

独立编译：

```bash
cmake -S Simulation -B build-simulation
cmake --build build-simulation --parallel 4
```

需要 ROOT、Geant4>=11.2的MT库、HEALPix。独立二进制位于build-simulation/bin；使用前加载同一套库和数据集环境。统一包装器默认选择build/bin。

主要调节 config/sim_config.json：源半径mm、是否前半球、自动锥额外半角degree、World材料/余量、Nside、能量上下限MeV及点数、每cell事例数、层阈值MeV。particle_name保持gamma，chamber保持0/1。完整表见 [总体手册](../MANUAL_CHN.md)。

config/run_config.json 的threads是每作业线程数；jobs决定作业分工；events_per_chunk决定落盘间隔；master_seed是整批随机种子；output_directory隔离批次。增加线程不增加总事例数。

日志输出actual gamma、每块emitted/hits/ch2/ch1/valid。首次小跑看到非零双层触发且正常合并后才放大。若全部valid=0，不要立即重跑亿级事件。未完成块没有正式ROOT，下次同计划运行会重算它；完成块会校验后跳过。
