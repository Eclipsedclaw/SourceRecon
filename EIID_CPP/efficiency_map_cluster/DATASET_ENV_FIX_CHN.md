# 数据目录已安装，但 G4LEDATA 未设置：启动脚本修复

## 已确认的事实

服务器的 `geant4-config --check-datasets` 显示 G4EMLOW8.5、G4ENSDFSTATE2.3 等目录均为 INSTALLED，但通过原启动脚本后，G4LEDATA 和 G4ENSDFSTATEDATA 仍未设置。

因此不是需要重新下载数据，也不是需要修改模拟参数，而是脚本只依赖 geant4.sh 导出路径，没有覆盖“数据目录存在、环境脚本未导出变量”的情况。此前依赖探针、编译、2 项 C++ 测试及 15 项 Python 测试已经在服务器通过；此次修复不需要重新编译 C++。

## 本次修改

`cluster/setup_env.sh` 加载已选中的 geant4.sh 后，再调用**同一 bin 目录**的 `geant4-config --datasets`。该官方命令输出每个数据集的名称、环境变量名和安装路径。

脚本保留该 geant4.sh 已提供的有效路径；没有有效路径时，从清单中补齐，并确认目录存在后才 export。不会从 PATH 挑另一版本的 geant4-config，不执行 eval，不下载数据、不修改系统配置。

目录确实不存在时，输出警告，不伪造路径；模拟器仍会拒绝缺少必需数据的运行。ROOT 合并及测试不需要 Geant4 物理数据，所以不会仅因某个物理数据目录缺失就被脚本强制禁止。

目录存在检查不等于逐个校验所有物理数据文件；实际物理运行仍需小跑验证。

## 已编译成功的服务器如何更新

将 `dist/efficiency_map_cluster_dataset_env_fix.zip` 上传到 `~/labwork/SourceRecon/EIID_CPP/`，执行：

```bash
cd ~/labwork/SourceRecon/EIID_CPP
unzip -o efficiency_map_cluster_dataset_env_fix.zip
cd efficiency_map_cluster
make run-local
```

这个增量补丁针对已经应用 G4Run 探针修复、且编译成功的版本；只含启动脚本、新增测试和相关说明文件。不包含参数 JSON、用户 environment.sh、C++ 源码、已有数据或构建产物。无需 clean/configure/all，也不必删除 smoke_001；已有有效分块仍会核对后跳过。

如希望先单独验证环境：

```bash
bash cluster/setup_env.sh bash -c 'printf "G4LEDATA=%s\nG4ENSDFSTATEDATA=%s\n" "${G4LEDATA:-未设置}" "${G4ENSDFSTATEDATA:-未设置}"'
```

在当前小服务器上，预期分别是 `/opt/geant4/geant4-11.2.2-install/share/Geant4/data/G4EMLOW8.5` 和同一父目录下的 `G4ENSDFSTATE2.3`。这些路径没有硬编码进脚本。

首次上传可使用完整源码包 `dist/efficiency_map_cluster_source_dataset_fixed.zip`，仍需在目标机器 configure/all。已有用户优先用增量包，以免覆盖自行修改的默认 JSON。

## 验证

新增 6 项 Bash 行为回归测试，验证变量恢复、指定安装优先、有效路径保留、目录缺失不伪造、查询失败及非法变量拒绝。测试使用临时目录和元数据脚本，不冒充实际 Geant4 物理模拟。本机未运行实际粒子输运，服务器小跑结果仍待确认。

参考：[Geant4 11.2.2 官方数据集查询命令源码](https://github.com/Geant4/geant4/blob/v11.2.2/cmake/Templates/geant4-config.in)。
