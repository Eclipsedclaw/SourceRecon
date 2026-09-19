# test5 已定位：依赖探针错误地孤立创建 G4Run

## 根因与证据

test5 的 `dependency-check.log` 显示，采用 Conda 的运行库后：

- 编译/链接通过，`ldd -r status: 0`，ROOT / Geant4 / libstdc++ 的路径匹配；
- ROOT 内存树创建、写入、读回、销毁均完成，HEALPix 检查完成；
- 最后阶段为 `13 G4Run passed; destroying G4Run`；
- 退出码为 139，堆栈明确落在 `G4Run::~G4Run()`。

[Geant4 11.2.2 官方源码](https://github.com/Geant4/geant4/blob/v11.2.2/source/run/src/G4Run.cc)中的析构函数会调用：

```cpp
G4RunManager::GetRunManager()->GetRunManagerType();
```

旧探针没有创建运行管理器，因此这里解引用空指针。这是依赖探针的使用错误，不是效率算法、输入文件或用户参数的问题。之前的 45 秒超时本身不能证明这个原因；本次新增阶段日志和崩溃堆栈才把问题定位清楚。

## 修复方式

`cmake/dependency_probe.cpp` 不再孤立创建 `G4Run`，改为调用真实 G4run 动态库中的 `G4RunManager::GetRunManager()`，确认未创建管理器时返回空指针。该查询不会创建探测器、初始化物理模型或运行事例。

保留真实 ROOT 写入/读回、HEALPix 计算、动态库路径/符号检查、正常退出检查；不通过跳过检查、泄漏 G4Run、提前强制退出或增加超时来规避崩溃。

正式模拟在 `Simulation/src/TaskRunner.cpp` 中先创建 `G4MTRunManager`，然后才运行事件，不是旧探针这种孤立使用方式。此次没有修改模拟物理源码、参数 JSON、用户 environment.sh 或 runs/ 数据。

## 更新与运行

已有项目：上传 `dist/efficiency_map_cluster_g4run_probe_fix.zip` 到服务器项目的父目录。该包包含先前构建/诊断补丁，不必逐个重装。

```bash
cd ~/labwork/SourceRecon/EIID_CPP
unzip -o efficiency_map_cluster_g4run_probe_fix.zip
cd efficiency_map_cluster
make configure && make all && make test && make run-local
```

不需要 `make clean`。`make configure` 会重新编译探针。命令用 `&&` 串联，前一步失败后不会继续执行模拟。若失败，请保留新的 `build/dependency-check.log`，不要删除 runs/。

全新上传可用 `dist/efficiency_map_cluster_source_g4run_fixed.zip`；已有项目用上面的补丁包，避免覆盖自己改过的默认 JSON。

## 验证范围

新增源码约束回归测试，禁止探针再次孤立创建 G4Run，禁止用强制退出隐藏析构错误。官方源码与 test5 堆栈相互吻合。

本机没有 ROOT / Geant4 / HEALPix 完整环境，尚未在服务器实际执行修复后的联合探针或 MT 模拟；因此修复这一处明确错误不等于完整模拟已验收。最新本地测试结果见 VALIDATION_CHN.md。
