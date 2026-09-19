# 2026-09-15：依赖检查超时的诊断补丁

后续 test5 已定位旧探针的 G4Run 析构崩溃，修复与最新补丁见 [G4RUN_PROBE_FIX_CHN.md](G4RUN_PROBE_FIX_CHN.md)。本页保留旧诊断过程；下面的阶段 12/13 描述针对旧探针，新探针改为安全查询运行管理器，不创建 G4Run。

## 这次日志说明什么

第一次检查因缺少 `GLIBCXX_3.4.31`、`CXXABI_1.3.15` 符号而链接失败；第二次显式链接 Conda 的 `libstdc++.so.6` 后，编译和链接成功，但检查程序运行超过了 45 秒。

这不能证明“还是编译器不兼容”，也不能证明物理模拟已成功。旧检查只有在读树结束后才输出消息，且没有立即刷新；因此这份旧日志不足以定位卡住的位置。

本补丁修复的是**诊断信息不足和报错误导**，不是宣称已消除服务器上的超时。没有改变物理源码、效率公式、参数 JSON、环境文件和已有 ROOT 数据。

## 如何使用

将 `dist/efficiency_map_cluster_probe_diagnostics.zip` 上传到服务器 `~/labwork/SourceRecon/EIID_CPP/`。它是累积补丁，包含之前构建补丁和本次诊断更新，不包含模拟结果或用户 JSON。

```bash
cd ~/labwork/SourceRecon/EIID_CPP
unzip -o efficiency_map_cluster_probe_diagnostics.zip
cd efficiency_map_cluster
make configure
```

现在先只执行配置，不必 `make clean`，也不必运行模拟。

如果仍失败，提供下面这份日志：

```bash
cat build/dependency-check.log
```

程序卡住期间，也可以在另一个终端查看进度：

```bash
tail -n 30 ~/labwork/SourceRecon/EIID_CPP/efficiency_map_cluster/build/dependency-check/probe.stderr.log
```

`dependency-check.log` 保留本次配置各次尝试的链接、库检查和运行结果；`probe.stdout.log` / `probe.stderr.log` 是最近一次运行尝试的输出，下次重跑会替换。配置顶层仍有带时间的 `configure_*.log`，不会删除旧的模拟日志。

## 如何解读新日志

- 编译/链接失败：查看编译器或链接器的具体报错。
- `ldd -r` 失败：查看缺失库、未解析符号或选中了错误安装路径；不会继续启动探针。
- 超时且没有 `01 main entered`：没有捕获到主函数入口，不能贸然判断是哪个库的问题。
- 停在 `01`：主函数已进入，正在调用 ROOT 初始化。
- 停在 `03`～`08`：具体的分支创建、写入或读回调用没有完成。
- 停在 `09`：ROOT 局部测试对象正在析构。
- 停在 `12` / `13`：正在构造 / 析构 G4Run。
- 停在 `16`：主函数准备返回，但进程尚未正常退出；不能把它当作检查通过。

成功仍要求实际读回正确数据、库路径检查通过、进程正常返回 0。没有跳过任何检查，也没有自动延长超时。

确有冷启动较慢的证据时，可**一次性诊断**较长等待是否有帮助：

```bash
make configure CMAKE_ARGS="-DEFF_PROBE_TIMEOUT_SECONDS=120"
```

这只是放宽等待时间，不是修复方法；仍须全部检查通过。该值保存在 CMake 缓存中，默认 45 秒，范围 1～600 秒。恢复默认用 `-DEFF_PROBE_TIMEOUT_SECONDS=45`。

配置成功后才继续：

```bash
make all && make test && make run-local
```

## 本地验证边界

14 项 Python 测试：13 通过，1 项 POSIX 文件锁测试因本机 Windows 跳过。新增测试实际编译标准 C++ 小程序，验证正常退出、退出码 3、带阶段消息超时、无阶段消息超时；并验证超时日志保留和准确分类。

本机没有完整 ROOT/Geant4/HEALPix 环境，不能替代服务器上的三库联合检查；未运行物理模拟。
