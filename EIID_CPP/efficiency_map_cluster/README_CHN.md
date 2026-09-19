# Efficiency Map Cluster：开发说明

本项目是独立的多线程原始效率打表工具，基于已经修正的 `raw_efficiency_map_experiment`。不调用重建算法，不生成 events.root，也不画图。历史版本保持不动。

用户操作请读 [MANUAL_CHN.md](MANUAL_CHN.md)。当前验证范围见 [VALIDATION_CHN.md](VALIDATION_CHN.md)。

## 架构与数据流

```text
efficiency_map_cluster/
├── config/                  # 物理、任务规模、集群资源、机器环境
│   ├── sim_config.json
│   ├── run_config.json
│   ├── cluster_config.json
│   └── environment.sh.example
├── common/                  # 配置、64位计数、任务编号、ROOT协议
│   ├── include/
│   ├── src/
│   ├── io/RootCountsIO.cpp
│   └── CMakeLists.txt
├── Simulation/              # 独立 Geant4 原生多线程模拟器
│   ├── include/
│   ├── src/
│   └── CMakeLists.txt
├── Merger/                  # 独立整数计数合并器；仅需 ROOT
│   ├── include/CountMerger.h
│   ├── src/CountMerger.cpp
│   ├── src/main.cpp
│   └── CMakeLists.txt
├── cluster/                 # 划分任务、HTCondor提交模板、日志与续跑
├── tests/                   # 计数、ROOT往返、任务与日志测试
├── third_party/             # 固定版本 JSON 单头文件及许可证
├── cmake/                   # 依赖定位、真实链接/启动检查、软件指纹
│   ├── DiscoverDependencies.cmake
│   ├── CheckDependencies.cmake / dependency_probe.cpp
│   └── BuildInfo.h.in
├── CMakeLists.txt / Makefile / configure.sh
├── README.md / README_CHN.md
├── MANUAL.md / MANUAL_CHN.md
└── runs/<批次名>/            # 运行时生成，不随源码包发布
    ├── manifest.json        # 冻结配置、全局事例范围
    ├── simulation.sub / merge.sub
    ├── submission_info.json
    ├── chunks/chunk_*.root  # 完成分块的整数计数
    ├── logs/*.log           # 所有运行输出和调度日志
    ├── .locks/             # 同一任务的进程互斥锁
    └── raw_efficiency_master.root
```

```text
JSON → prepare_jobs → manifest
                       ↓
          多个 Condor 作业（每个作业内 Geant4 多线程）
                       ↓
             每线程局部计数 → 主线程汇总
                       ↓
                  chunk_*.root
                       ↓
             efficiency_merge（严格校验）
                       ↓
            raw_efficiency_master.root
                       ↓
             scp 到小服务器 → 原有 Quicklook
```

## 模块职责与可替换点

- `common`：ConfigManager 检查物理参数；Campaign 检查整批事件范围；CellCounts 保存整数计数。ROOT I/O 与纯计数库分离。
- `Simulation`：G4MTRunManager 管理 worker；ActionInitialization 分别创建每线程的粒子枪、EventAction、RunAction。EfficiencyRun::Merge 合并线程计数。只有主线程调用 ROOT 写盘。
- 源位置由 `ISourceGeometry` 接口提供，当前实现为 `Ch2CenteredHemisphereSource`。
- 发射锥由 `IEmissionConePolicy` 接口提供，当前实现为 `AutoBoundingConePolicy`。
- 原几何、TrackerSD 和 Livermore 物理列表保留；配置类保留 ConfigManager 名称，以便复用几何代码。
- `Merger` 不链接 Geant4/HEALPix：依靠 manifest 的已知 RING 索引与计数协议合并。能单独部署到只装 ROOT 的机器。
- `cluster` 只用 Python 标准库。执行包装器负责日志和锁，不侵入物理代码。

各模块目录有各自的 README/MANUAL 中英文副本。

## 物理定义

每个 cell = 一个 HEALPix 方向中心 × 一个入射能量点。源位置是 ch2 中心加上“半径 × 方向”，不是把源放在坐标原点。

每个 cell 内，gamma 在覆盖探测器触发包络的圆锥内按立体角均匀发射。触发仍为 ch2（0）和 ch1（1）各自的总沉积能量超过阈值，不要求完全吸收。

原始绝对效率为：

```text
N = 该 cell 所有分块的 emitted_count 之和
k = 该 cell 所有分块的 valid_count 之和
f = (1 - cos(自动计算的圆锥半角)) / 2
efficiency = (k / N) * f
```

不添加 Jeffreys 平滑，不添加正数 baseline。N>0、k=0 保持效率为零；未模拟的后半球 N=0，也保留为零，但两者能从 emitted_count 区分。

4π 修正隐含条件：锥外发射不能产生本模型接受的触发。默认真空环境及既有触发包络沿用原实验。若改成空气、添加周围散射材料，或认为后方材料反散射贡献不可忽略，需要额外验证包络是否覆盖所有贡献；单纯乘 f 不会补偿漏掉的锥外路径。

这仍是原有几何/物理选择下的探测效率，不自动包含真实仪器未建模的读出损失、死时间等。

## 并行、编号和续跑约定

1. 总事例数由方向数 × 能量点数 × particles_per_cell 决定。线程数/作业数只改变分工，不乘大这个总数。
2. 全局事例号用 uint64；局部一次 BeamOn 的事例数不超过 INT_MAX。一个 cell 可以跨多个分块。
3. 主随机种子和全局事例号混合得到 Ranecu 种子。样本编号不依赖 worker 编号；同一软件环境下支持重试和线程调度变化。不同 Geant4/编译器环境不承诺逐位复现，也不允许混合到同一批次。
4. worker 只更新自己的稀疏计数表。每个分块结束后才合并和写 ROOT。
5. .tmp 文件不算完成。完成文件经过读回检查后以同文件系统 rename 发布。
6. 重试先检查已有块的身份、配置、软件信息及计数。已完成块跳过，未完成块重算；不从半个事件恢复。
7. 合并按 manifest 指定的完整事件覆盖计算；缺块、重复索引、未知 ROOT 块、混合配置/软件、计数异常都会失败。
8. 最终文件已经存在时，逐行复核，不静默覆盖。检查与合并本身也有独立日志。

程序包装器使用共享文件系统的 flock。需确保集群挂载支持跨节点文件锁；不要绕过包装器同时启动相同 job_id。

## 文件协议

分块 ROOT：

- TNamed `chunk_metadata`：完成标志、批次/分块身份、冻结配置、源码指纹、编译器和依赖版本。
- TTree `ChunkCounts`：cell_index、emitted_count、valid_count、hit_count、front_count、rear_count（ULong64_t），cone_solid_angle_fraction（Double_t）。

最终 ROOT：

- TTree `RawEfficiency`：cell_index、emitted_count、valid_count（ULong64_t）；efficiency、cone_solid_angle_fraction（Double_t）。
- 元数据：healpix_nside、healpix_ordering、direction_count、energy_count、energy_min_MeV、energy_max_MeV、source_radius_mm、efficiency_definition。
- `requested_event_count_u64`：字符串形式的大事例数，避免有符号转换溢出。
- `campaign_metadata`：manifest、软件信息和完成标志。

cell_index = direction_index * energy_count + energy_index。RING 从 +Z 到 -Z 排列；前半球采用 z<=0，包含赤道中心像素。最终输出完整天空索引，所以能直接供现有 raw Quicklook 读取；没有把中间文件拼成含重复 cell 的最终树。

## 依赖与测试

- CMake >=3.20，Linux C++17 编译器（实际标准按 ROOT/Geant4 要求自动提高，例如 C++20）。
- ROOT >=6.28，Geant4 >=11.2 的 **MT共享库构建**，HEALPix C++；Python >=3.8。
- TTreeReader 必需的 TreePlayer 可能间接依赖 ROOT 图形库，但不创建 GUI、画图或链接 Geant4 Qt/OpenGL 驱动；保留几何中的基础显示属性。
- 不下载、安装或替换用户的 ROOT/Geant4。nlohmann/json 固定为 3.11.3，随源码附带许可证。

`make test` 不做物理大模拟；计数/ROOT/任务日志测试用固定夹具，不受用户生产配置改动影响。多线程输运和统计质量必须在真实 Geant4 环境小跑确认。

构建自检由 cmake/DiscoverDependencies.cmake 和 CheckDependencies.cmake 实现：有限目录自动定位，实际编译/链接/启动内存检查，Linux 核对 ldd -r 的库路径与未解析符号。默认链接不兼容时仅尝试 ROOT 同目录 libstdc++，通过后由 eff_runtime 统一传递；eff_root_io PUBLIC 链接 TreePlayer，三个消费者无须分别补库。配置失败删除 configure.ok，日志保留在 build/。不下载依赖，不改变物理逻辑。

## 设计参考

cluster/setup_env.sh 的数据路径加载同时检查同一安装的 geant4.sh 和 geant4-config --datasets：前者未设置有效目录时，用后者的清单补齐。只查询元数据、不 eval 文本、不自动安装数据；tests/test_dataset_environment.py 覆盖此行为。详见 [DATASET_ENV_FIX_CHN.md](DATASET_ENV_FIX_CHN.md)。

依赖探针必须遵守 Geant4 对象生命周期：不在缺少运行管理器的情况下创建 G4Run；使用 G4RunManager::GetRunManager() 安全查询来检查 G4run 库可调用。正式模拟的管理器仍由 TaskRunner 持有。test5 的修复依据与回归边界见 [G4RUN_PROBE_FIX_CHN.md](G4RUN_PROBE_FIX_CHN.md)。

- [INPAC HTCondor 使用与资源规则](https://inpac.sjtu.edu.cn/cluster-help/px/condorquickguide.html)
- [INPAC 文件系统](https://inpac.sjtu.edu.cn/cluster-help/px/filesystem.html)
- [Geant4 官方多线程结构](https://geant4.web.cern.ch/documentation/pipelines/master/bftd_html/ForToolkitDeveloper/OOAnalysisDesign/Multithreading/mt.html)
