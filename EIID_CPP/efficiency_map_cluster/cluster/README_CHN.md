# cluster：开发说明

Python标准库与Bash实现的批处理外壳，不含物理模型或ROOT绘图。

```text
cluster/
├── prepare_jobs.py         # 配置冻结、分块清单与提交文件
├── workflow.py             # 本机/集群入口、日志、锁与信号
├── setup_env.sh            # 匹配编译环境的库及数据集
├── run_job.sh              # Python启动薄封装
├── simulation.sub.in       # 模拟作业模板
└── merge.sub.in            # 合并作业模板
```

prepare_jobs在任何计算前冻结JSON、验证64位规模并生成连续全局事件区间；每块按id%jobs分配到作业。再次prepare只允许同一计划，保留campaign_id。

workflow以Python子进程捕获stdout/stderr字节流并实时tee。每次启动使用新的日志名；内核文件锁阻止同job并发；TERM/INT/HUP转发到子进程组，退出状态保留。SIGKILL/断电不可能保证最后缓冲数据已写入，应结合Condor日志判断。

setup_env加载机器本地环境及CMake固定库路径，清除旧Geant4数据变量后加载匹配脚本。共享存储使用should_transfer_files=NO，threads同步到request_cpus；不自动提交，也不把环境路径写死在源码。

submit-merge仅在所有预期分块文件出现后提交；真正的内容/计数校验仍在计算节点Merger中完成，不在登录节点读取大ROOT。

