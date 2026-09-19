# 2026-09-13 构建修复：已有源码怎样更新

后续数据环境修复：编译和测试已经通过，但 INSTALLED 的数据目录未导出为 G4LEDATA 等变量时，使用 `dist/efficiency_map_cluster_dataset_env_fix.zip`，按 [DATASET_ENV_FIX_CHN.md](DATASET_ENV_FIX_CHN.md) 更新脚本后直接 `make run-local`。该增量包不要求重新编译。

最新更新：test5 已明确定位为探针孤立创建 G4Run 后的析构崩溃。使用 `dist/efficiency_map_cluster_g4run_probe_fix.zip`，步骤见 [G4RUN_PROBE_FIX_CHN.md](G4RUN_PROBE_FIX_CHN.md)。下面两次旧补丁记录仅供追溯。

2026-09-15 补充：若第二次链接成功但显示 `Process terminated due to timeout`，请使用新的累积包 `dist/efficiency_map_cluster_probe_diagnostics.zip`。步骤和诊断范围见 [PROBE_TIMEOUT_CHN.md](PROBE_TIMEOUT_CHN.md)。它补全阶段日志，不代表服务器超时根因已被修复。以下保留上次构建修复说明。

本次只更新构建、环境包装器、相关测试和说明书。不改物理源文件，不改三个参数 JSON，不改 environment.sh，不包含或删除 runs/ 下的任何结果。

## 已上传旧版的用户

将 `dist/efficiency_map_cluster_build_fix.zip` 上传到服务器的 `~/labwork/SourceRecon/EIID_CPP/`（项目的父目录），执行：

```bash
cd ~/labwork/SourceRecon/EIID_CPP
unzip -o efficiency_map_cluster_build_fix.zip
cd efficiency_map_cluster
make configure && make all && make test && make run-local
```

补丁包中每个文件均以 efficiency_map_cluster/ 开头，故必须在父目录解压。`-o` 只替换包内列出的构建/文档文件，不会删除其他文件。不要用 `unzip -n` 更新：它会跳过已存在的旧 CMakeLists.txt，导致仍使用旧配置。

仅想编译验证、不发射粒子：执行到 `make test` 即可，不执行 run-local。已有 smoke_001 的 manifest 可保留；尚未生成 ROOT 分块的失败批次可直接继续。

首次上传用已更新的完整源码包 efficiency_map_cluster_source.zip。已有用户优先使用补丁包，避免覆盖自行调整的默认 JSON。

## 修复内容

1. 公共 IO 库 PUBLIC 链接 ROOT::TreePlayer，修复模拟器、合并器和 ROOT 测试的 TTreeReader 未定义符号。
2. 自动定位常见 Conda/Geant4 安装，环境文件仅作可选覆盖。
3. 默认链接失败时试用 ROOT 同目录的 libstdc++.so.6，实际链接/启动验证通过后才采用；不更改系统库。
4. 实际检查 ROOT 内存读回、HEALPix、G4run 库查询和 Linux 动态库路径。不建探测器、不做输运；不孤立创建 G4Run 对象。
5. 配置失败清除成功标记；未成功编译不得启动 run-local。

如果配置仍失败，请保留 `build/dependency-check.log` 和最新 `build/configure_*.log`。明确的 FAILED 表示该组合未通过验证，不应继续提交大任务。日志中的 CMake 路径冲突警告不会被隐藏；实际加载的库还会独立检查。

本机只做了不依赖完整物理软件栈的验证，具体范围见 VALIDATION_CHN.md；不能把这些验证等同于服务器上的真实 Geant4 MT 小跑。
