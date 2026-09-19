# 本次交付的自检记录

## 2026-09-15 数据路径恢复

- 用户提供的服务器输出已确认上一轮修复后依赖探针成功、模拟器及合并器编译成功、C++ 测试 2/2 与 Python 测试 15/15 通过；模拟因 G4LEDATA 未设置停止。数据检查显示全部预期目录存在。
- 本次仅修改 cluster/setup_env.sh 的数据环境加载，使用同一安装的 geant4-config --datasets；不改任何 C++、CMake、物理参数或数据文件。
- 新增 6 项临时目录/元数据脚本的环境行为测试全部通过；Bash 语法检查通过。
- 本轮完整 Python 测试 21 项：18 通过，3 跳过（本机没有常驻 CMake，跳过 2 项此前已验证的 CMake 诊断测试；Windows 跳过 POSIX 文件锁）。没有重新安装工具来重跑未修改的 CMake 逻辑。
- 新脚本尚待服务器运行验证。本机没有完整物理依赖，未进行真实粒子输运；目录存在不等于已校验数据集内每个文件完整性。

## 2026-09-15 test5：G4Run 析构崩溃修复

- test5 堆栈落在 G4Run::~G4Run；与官方 11.2.2 源码核对，旧探针缺少运行管理器却孤立创建 G4Run，导致析构空指针访问。
- 探针改用 G4RunManager::GetRunManager() 安全查询，真实动态库调用、ROOT/HEALPix 检查和正常退出检查保留。正式模拟源码、参数和运行包装器不变。
- 本轮 Python 15 项：14 通过，1 项 POSIX 文件锁在 Windows 跳过（CMake3.31.6、GNU15.2）。新增源码约束测试防止再次引入孤立 G4Run 或强制退出；该测试不是实际 Geant4 运行测试。
- 本机仍没有完整 ROOT/Geant4/HEALPix。已修复这处明确的 API 使用错误，但修复后的三库联合探针和 MT 模拟尚待服务器执行，不能将本地测试等同于完整模拟验收。

以下保留此前各轮验证记录。

## 2026-09-15 超时诊断补充

- 用户新日志中，显式使用 Conda libstdc++ 的第二次编译/链接已成功，探针随后超时；旧日志不能确定卡住位置。
- 本次仅补全阶段消息、超时分类，并把 Linux 库检查移到启动之前；未修复或确认服务器超时根因。
- Python 14 项中 13 通过、1 项 POSIX 文件锁测试在 Windows 跳过。新增标准 C++ 可执行程序测试四种运行结果：成功、返回 3、带消息超时、无消息超时；正确保留超时前输出，不使用伪造 ROOT/Geant4 头文件。
- 本机仍缺少完整 ROOT/Geant4/HEALPix，未执行实际联合探针或粒子输运。
- 统一纯 common 模式重新配置、编译成功，CTest 1/1 通过（GNU15.2、C++17、CMake3.31.6）。

## 2026-09-13 构建修复补充

- 补齐 PUBLIC TreePlayer 链接；依赖定位、实际链接/启动检查与共享运行库选择均集中在 CMake，不修改物理源文件及三个参数 JSON。
- 本机重新执行统一纯 common 构建和独立 common 构建：GNU15.2/C++17，均编译通过且各自 CTest 1/1 通过。
- Python 回归共12项：11通过，1项 POSIX flock 在 Windows 跳过。新增5项覆盖 TreePlayer 传递、配置失败撤销标记并保留日志、残留缓存不得编译/运行、运行路径无空项、ldd 路径比较拒绝错误库。
- 用真实 CMake 验证缺少 ROOT 时配置失败、不产生 configure.ok；Bash 两个修改脚本通过语法检查。
- 与原交付 ZIP 按 SHA256 对比，Simulation 物理源码、common 配置/计数/ROOT读写源码、生产参数 JSON 均未修改。
- **本机仍没有 ROOT/Geant4/HEALPix，未实际执行新的三库联合链接探针，也未运行真实 MT 输运。** 探针会在服务器 make configure 时真实执行；失败则拒绝构建，详情写入 dependency-check.log。人工 ldd 文本和模拟 cmake 退出码只用于入口逻辑测试，不代表物理依赖测试通过。
- 服务器旧日志证明过原版 C++ 源码可编译，但 ROOT 消费者链接失败；本次不能据此声称已经在服务器链接成功。

以下保留首次交付记录，便于区分历史验证与本次验证。

日期：2026-09-13。此记录区分实际执行和未执行，不把源码检查当作物理模拟验收。

## 已实际通过

| 检查 | 结果 |
|---|---|
| 公共C++库统一构建 | GNU15.2，C++17，CMake3.31.6，编译通过 |
| common模块独立构建 | 编译及CTest通过 |
| C++计数测试 | CTest 1/1通过：manifest读取、跨cell分块边界、缺失/错误计数拒绝、零计数、合并、uint64大事例数、无效配置、种子一致性 |
| Python任务/日志测试 | 7项中6项通过，1项POSIX flock检查在Windows跳过 |
| Python测试覆盖 | 精确分块、64位总数、非法参数、冻结计划、EL7/EL9模板、stdout/stderr合并、非零退出码保留、多次日志不覆盖、job参数解析 |
| Merger与ROOT测试调用代码 | g++ -fsyntax-only通过；这不包括含ROOT头文件的RootCountsIO.cpp，也不是ROOT链接测试 |
| Bash脚本 | configure.sh、setup_env.sh、run_job.sh分别通过bash -n；均为LF换行 |
| Make入口 | make -n smoke显示先编译再prepare/run-local，没有实际启动模拟 |
| 基线物理文件 | DetectorConstruction、DetectorMessenger、TrackerHit、TrackerSD、MyPhysicsList的头/源共10文件与原版SHA256一致 |
| Geant4接口 | 只读核对官方11.2.2 CMake目标、multithreaded组件、线程数量接口 |
| 外部任务 | 没有连接cluster提交作业，没有生成或覆盖任何用户ROOT数据 |

测试使用tests/fixtures固定小配置；不会因用户修改正式JSON而改变预期值。

## 尚未执行

本机Windows开发环境没有ROOT、Geant4与HEALPix整套依赖，因此以下仍需在小服务器完成：

- Simulation的完整编译链接，以及真实Geant4 MT输运运行；
- RootCountsIO的真实ROOT编译、写盘/读回测试（make test包含test_root_io）；
- Linux/Lustre跨节点flock行为、HTCondor实际提交与抢占恢复；
- 大统计性能和效率统计误差评估。

未使用伪造的ROOT/Geant4接口来宣称这些测试通过。请按MANUAL_CHN第一节小跑，确认非零双层触发和正常合并后再放大。

## 已在自检中修正的事项

- JSON复制初始化明确使用圆括号，避免单元素数组；
- CMake最低版本与实际命令一致，独立模块生成头文件路径正确；
- make smoke在并行make下也先完成编译再运行；
- 已存在最终ROOT不是简单跳过，而是按计数和网格元数据重新核对；
- 写完ROOT先读回，再发布正式文件；
- 每次应用日志使用唯一文件名，并保留子进程失败退出码；
- 老EL7节点的OS属性提供兼容筛选，不强制依赖EL9新增标记。

临时验证工具/本地构建产物不进入源码压缩包。包内没有小服务器环境路径锁定文件，也没有模拟结果。
