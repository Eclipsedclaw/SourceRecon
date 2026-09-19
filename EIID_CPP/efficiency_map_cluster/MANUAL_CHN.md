# Efficiency Map Cluster：操作说明

目的：在小服务器先确认可用，再到 cluster 大规模生成原始效率 ROOT。cluster 不画图，完成后把最终文件复制回小服务器。

已上传旧源码的用户：本次补丁更新方法见 [BUILD_FIX_CHN.md](BUILD_FIX_CHN.md)，无需重传 JSON 或删除结果。

## 一、先做这两步

### 1. 小服务器：编译并小跑

将整个源码文件夹上传到小服务器；进入项目根目录：

```bash
cd ~/labwork/SourceRecon/EIID_CPP/efficiency_map_cluster
```

通常不必创建 environment.sh。configure 自动查找当前环境、常见 root-env、/opt/geant4/*-install，并实际做链接/启动检查。已有 environment.sh 保持不动；模板全为注释，复制模板本身不会加载环境。

```bash
make configure &&
make all &&
make test &&
make run-local
```

默认试跑：Nside=2、仅 0.662 MeV、28 个前半球方向、每 cell 10000 粒子，共 **280000** 粒子。2 个作业在本机依次执行，每个作业内使用4个 Geant4 worker；共4个分块。

完成时看 `Valid two-layer triggers` 和 `Positive cells` 是否大于0，且没有 Fatal/计数检查错误即可进入下一步。不需要再跑一套漫长验收。小统计只是验证通路，不代表效率误差足够小。

最终文件：`runs/smoke_001/raw_efficiency_master.root`。
所有运行日志：`runs/smoke_001/logs/`。
`make smoke` 等价于增量编译后执行 run-local（仍需先 configure）。

### 2. Cluster：加大事例数并提交

只上传源码，不复制小服务器的 build 目录、二进制、environment.sh、已有 runs。项目和输出放在计算节点可访问的共享目录，例如本组分配的 /lustre 路径。

在 cluster 使用与目标节点 OS 匹配的依赖重新编译。自动查找不到课题组自定义安装时，才用可选的 `config/environment.sh` 加载课题组指定的环境（不会递归搜索整个共享磁盘或自动安装软件）：

```bash
make configure
make all
```

然后修改下文三个 JSON。**正式批次换一个新的 output_directory，例如 ../runs/production_001。**

```bash
make prepare
make submit
condor_q
```

prepare 只生成计划，不运行。submit 才提交 HTCondor。所有模拟作业完成后：

```bash
make submit-merge
condor_q
```

合并也在计算节点执行，不在登录节点处理大型数据。成功输出在所配置批次目录下的 `raw_efficiency_master.root`。

大规模运行不要使用 `make run-local` 或直接在登录节点执行模拟器。无需默认申请长时队列；分块支持中断后重算未完成块。

## 二、可以调整哪些参数

### config/sim_config.json：物理与网格

| 完整字段 | 含义与约束 |
|---|---|
| source.particle_name | 固定 gamma，避免误发射默认 geantino |
| source.hemisphere_radius_mm | 点源距离 ch2 中心的半径，mm；默认5000，可改 |
| source.front_hemisphere_only | true 只模拟相机前半球 z<=0；false 模拟全天球 |
| source.emission_cone_safety_margin_degree | 自动包络锥额外增加的半角，度；默认1，范围[0,45)。不是总锥角 |
| environment.world_material | 默认 G4_Galactic 真空；可选 G4_AIR。空气会引入沿途散射，须重新验证定向锥的效率估计前提 |
| environment.world_margin_mm | World 在源半球/探测器包围范围外的余量，mm，正数 |
| grid.healpix_nside | HEALPix 分辨率，2的幂，1至8192；越大格点和内存越多 |
| grid.energy_point_count | 能量采样点数，正整数；不是每个事件的能量沉积分支数 |
| grid.energy_min_MeV | 入射能量点的下限，MeV，>0 |
| grid.energy_max_MeV | 上限，MeV；多点时大于下限，单点时必须等于下限 |
| grid.particles_per_cell | 每个有效方向—能量 cell 的总发射数，正整数，支持64位；不是每线程数量 |
| trigger.front_chamber_id | 保持0，对应ch2；与当前几何绑定 |
| trigger.rear_chamber_id | 保持1，对应ch1；与当前几何绑定 |
| trigger.minimum_layer_energy_MeV | ch2与ch1各自的能量阈值，MeV；两个沉积总和分别严格大于阈值才算有效 |

能量点包含上下端点并等间隔；只画0.662切片的短测试就用单点0.662。不需要为此模拟整条能谱。

```text
全天球方向数 = 12 * Nside²
前半球方向数（含赤道）= 6 * Nside² + 2 * Nside
总事例数 = 有效方向数 * energy_point_count * particles_per_cell
```

例如 Nside16、50能量点、每cell100000粒子，前半球总计78.4亿粒子。先依据小跑耗时估算，不要把“小数字的 JSON”误当成小任务。

### config/run_config.json：并行、分块、输出

| 字段 | 含义与约束 |
|---|---|
| threads | 每个作业的 Geant4 worker 数，1至18；自动写入 request_cpus |
| jobs | 这一批提交的作业数；本模板限制 jobs*threads<=300，且不能多于分块数 |
| events_per_chunk | 每次 BeamOn 的粒子数/落盘间隔，1至2147483647；允许一个cell跨块 |
| master_seed | 正整数随机种子；由它和全局事例号决定事件随机流 |
| output_directory | 本批次独立输出目录，相对于这份 run JSON 所在目录，不是当前终端目录 |

threads 增大不保证等比例加速。初期可选4或8线程/作业。chunks 较小可减少中断损失，但太小会增加调度/写盘开销。默认70000只针对小跑；生产可先用1000000，再依据实际每块耗时调整。

示例组合：8线程×16作业=128核；注意把账号其他在跑作业也计入资源占用。计划生成后物理参数、N、种子、threads/jobs/chunk 更改均要求换一个新 output_directory。

### config/cluster_config.json：HTCondor资源

| 字段 | 含义 |
|---|---|
| request_memory_mb | 单个模拟作业的总内存申请，MB，不是每线程值 |
| request_disk_mb | 单个作业的磁盘资源申请，MB；共享目录配额仍要自行确认 |
| merge_memory_mb | 合并作业内存，MB |
| target_os | auto 从准备计划的 Linux 系统识别；也可 EL7 或 EL9。必须和实际编译环境/依赖一致 |
| python_executable | 计算节点可直接执行的 Python >=3.8 的绝对路径，默认 /usr/bin/python3；必要时改为课题组的 Python |
| requirements | 额外 Condor 单行筛选表达式，默认空；不要无故限制节点 |

EL9 自动生成站点要求的两个字段。EL7 优先识别站点 EL7 属性，并兼容标准 CentOS7/RedHat7 字段；若长期 Idle，用 `condor_q -analyze` 核实节点属性和可用资源。不要把 EL9 的二进制强行投到 EL7。

按站点当前规则每作业最多18核；模板把本批次上限收紧到300核。程序不会绕过调度器限制。

### config/environment.sh：可选的机器环境覆盖

不是 JSON，不是必填文件。自动定位失败或必须选择特定工具链时，用它 source 课题组环境，配置 CMAKE_PREFIX_PATH、PATH、CXX。不要猜集群安装路径，也不要把旧 Geant4 10.x 环境与新程序混用。

configure 固定选中的库位置，生成 `build/runtime_paths.sh`。正式运行包装器优先使用这些库，并重新加载匹配的 geant4.sh 数据集，减少旧 LD_LIBRARY_PATH/G4数据集混入问题。它不是可跨机器复制的配置。

若 geant4.sh 未导出数据变量，包装器会用同一 bin 目录的 `geant4-config --datasets` 补齐已存在的数据目录；不会使用 PATH 中另一版本的工具，不下载数据。出现“INSTALLED 但 G4LEDATA 未设置”时，按 [DATASET_ENV_FIX_CHN.md](DATASET_ENV_FIX_CHN.md) 更新启动脚本即可，无需重编译或修改物理参数。

配置包含真实的内存 TTreeReader 读回、HEALPix 像素和 G4run 动态库查询检查，Linux 还检查 ldd -r 的实际库路径。不孤立创建 G4Run，不进行粒子输运，不生成效率 ROOT。系统默认链接不兼容时，会尝试 ROOT 同目录的 libstdc++.so.6，通过检查才统一应用到所有 ROOT 消费者。不会替换系统库。

旧探针若在 `destroying G4Run` 之后以 139 崩溃，请按 [G4RUN_PROBE_FIX_CHN.md](G4RUN_PROBE_FIX_CHN.md) 更新。该错误来自探针缺少运行管理器，不需修改模拟参数或清除数据。

日志位于 `build/configure_时间_进程号.log` 和 `build/dependency-check.log`。配置失败不会留下有效 configure.ok，make all/run-local 不会继续执行。不能把 CMakeCache.txt 存在当成成功。

依赖探针的逐阶段消息会立即写入 `build/dependency-check/probe.stderr.log`，运行期间可用 `tail` 查看；超时会打印最后执行阶段，不再笼统报为编译器不兼容。默认超时 45 秒；`make configure CMAKE_ARGS="-DEFF_PROBE_TIMEOUT_SECONDS=120"` 可修改等待时间（缓存保存，范围 1～600 秒），但不能跳过检查。没有明确慢启动证据时，应先定位卡住阶段而不是不断加长时间。详情见 [PROBE_TIMEOUT_CHN.md](PROBE_TIMEOUT_CHN.md)。

## 三、常用操作

| 目的 | 在项目根目录执行 |
|---|---|
| 配置编译依赖 | make configure |
| 编译全部 | make all |
| 只编译模拟器 | make simulation |
| 只编译合并器 | make merger |
| 快捷软件测试，不跑物理大模拟 | make test |
| 仅生成/核对清单 | make prepare |
| 本机运行并合并，自动记录日志 | make run-local |
| cluster提交模拟 | make submit |
| cluster提交合并 | make submit-merge |
| 本机核对所有分块和已有最终文件，不创建结果 | make check |
| 本机合并；已存在结果则逐行复核 | make merge |

run-local 不重新编译。修改 JSON 后不必重新编译，但旧批次计划不能原地换参数。重新编译也不会删除 runs。

使用另一套配置：

```bash
make prepare SIM_CONFIG=config/my_sim.json RUN_CONFIG=config/my_run.json
make run-local SIM_CONFIG=config/my_sim.json RUN_CONFIG=config/my_run.json
make submit SIM_CONFIG=config/my_sim.json RUN_CONFIG=config/my_run.json CLUSTER_CONFIG=config/my_cluster.json
make submit-merge RUN_CONFIG=config/my_run.json
```

每次命令要传入对应 RUN_CONFIG，避免操作了默认 smoke 批次。

只重试某个本地作业，仍保留完整日志：

```bash
python3 cluster/workflow.py job --manifest runs/smoke_001/manifest.json 0
```

直接执行二进制的接口如下；直接运行不会自动 tee 到日志，通常优先使用以上包装命令：

```bash
bash cluster/setup_env.sh build/bin/efficiency_simulator runs/smoke_001/manifest.json 0
bash cluster/setup_env.sh build/bin/efficiency_merge runs/smoke_001/manifest.json --check-only
```

## 四、断点、失败与日志

- 每个作业一次启动对应一个 `job_0000_attempt_时间_随机后缀.log`。stdout 与 stderr 合并实时记录，不只保存最后几十行。
- 开头记录时间、机器名、命令；模拟器记录软件/数据集、配置、线程/种子及分块信息；正常结束记录 exit_status。
- 每次重试新增日志，不覆盖上一次；多个作业不写同一个应用日志。
- `scheduler.log` 记录排队/抢占等调度事件，Condor .out/.err 为启动器本身保底。
- 断电或 SIGKILL 无法保证最后一段缓冲内容/结束标记已写入；此时必须看调度器日志，不能靠“文件存在”判断成功。
- 再次运行同一批次，合格的已完成块自动跳过。先用 condor_q 确认没有同批次的旧作业仍在运行，再重新 submit，避免占用重复队列资源。
- .tmp 文件不会参与合并。不要为了重跑删除全部结果。
- 若某个正式 chunk 损坏，先把该文件移到 chunks 目录以外保存，然后只重试负责该块的 job。未知 .root 留在 chunks 会被合并器拒绝。
- 最终 ROOT 损坏时，把它移走留存，保留所有 chunks，再 merge/submit-merge。
- 全零计数允许写出，但日志会警告。若 emitted正常而全图valid=0，不要盲目增加亿级事例；检查 actual gamma、hit、ch2/ch1 及配置。

## 五、拿回小服务器画图

把最终 `raw_efficiency_master.root` 从 cluster scp 到小服务器即可；需要debug时一起复制 logs。不用搬全部 chunks 才能画图。

假设已经复制为小服务器的 `/home/ezqi/raw_efficiency_master.root`，在小服务器运行：

```bash
cd ~/labwork/SourceRecon/EIID_CPP/raw_efficiency_map_experiment/Quicklook
root -l -b -q 'run_raw_efficiency_map.C("/home/ezqi/raw_efficiency_master.root","cluster_figures")'
```

它调用你原有的矩形图和 skymap 绘图器，选0.662 MeV，输出到该 Quicklook 下的 cluster_figures。这不是在 cluster 上绘图；新项目没有带绘图代码。

若改模拟全天球，原 Quicklook 中 frontHemisphereOnly 的设置也要对应修改，避免把真实后半球误标为未模拟。本次程序没有替你改它。

## 六、独立编译与手动指定依赖

整个项目：

```bash
make configure CMAKE_ARGS="-DCMAKE_PREFIX_PATH=/实际ROOT前缀\;/实际Geant4前缀\;/实际HEALPix前缀"
make all JOBS=4
```

也可以仅在当前命令指定前缀：`CMAKE_PREFIX_PATH=/实际ROOT前缀:/实际Geant4前缀 make configure`。若不自动识别，可直接指定：

```bash
cmake -S . -B build -DROOT_DIR=/实际路径/lib/cmake/ROOT -DGeant4_DIR=/实际路径/lib/cmake/Geant4 -DHEALPIX_INCLUDE_DIR=/实际路径/include/healpix_cxx -DHEALPIX_LIBRARY=/实际路径/lib/libhealpix_cxx.so -DEFF_GEANT4_CONFIG=/实际路径/bin/geant4-config
```

有静态 cxxsupport 时加 `-DCXXSUPPORT_LIBRARY=/实际路径/lib/libcxxsupport.a`。不要拿示例中的“实际路径”原样执行。

若自动兼容检查仍失败，应先读 dependency-check.log，不要继续 make all。可显式传 `-DEFF_CXX_RUNTIME_LIBRARY=/兼容目录/libstdc++.so.6`；仍须通过真实链接和启动检查。若需要换编译器，把旧 build 改名备份（不要删除 runs），再用 `CXX=/实际编译器路径 make configure`。只改 C++17/20 不能解决 GLIBCXX/CXXABI 运行库缺失。自动配置不保证任意 ROOT/Geant4/操作系统组合都兼容。

模块独立构建：

```bash
cmake -S common -B build-common
cmake --build build-common --parallel 4
cmake -S Merger -B build-merger -DCMAKE_PREFIX_PATH=/实际ROOT前缀
cmake --build build-merger --parallel 4
cmake -S Simulation -B build-simulation
cmake --build build-simulation --parallel 4
```

common 纯计数部分不用 ROOT/Geant4；Merger 只需 ROOT；Simulation 需三套依赖。模块模式可执行文件也在对应 build-*/bin。自动工作流默认只找统一构建的 build/bin，不会自行选择这些独立构建。

源码符合C++17；如 ROOT 要求C++20，CMake会自动提高标准，不是服务器“只有C++20”。换编译器或整套库建议新建构建目录；不能混用旧对象文件。

Makefile 是入口薄封装，库链接请在 CMake 参数或 environment.sh 指定，不要继续手工到每个模块堆 -I/-L/-l。只清理编译产物可执行 `cmake --build build --target clean`，不会删除 runs。

## 七、验收边界

源码内置了快速软件测试，但交付机器没有 ROOT/Geant4，尚未在这里完成真实 MT 输运运行。请先执行第一节小跑；观察非零触发与正常合并后再放大。具体已执行/未执行的检查写在 VALIDATION_CHN.md。
