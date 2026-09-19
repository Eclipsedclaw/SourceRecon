# cluster：操作说明

```text
cluster/
├── prepare_jobs.py         # 配置冻结、分块清单与提交文件
├── workflow.py             # 本机/集群入口、日志、锁与信号
├── setup_env.sh            # 匹配编译环境的库及数据集
├── run_job.sh              # Python启动薄封装
├── simulation.sub.in       # 模拟作业模板
└── merge.sub.in            # 合并作业模板
```

1. 执行 make configure 自动定位并检查依赖，然后 make all。仅自定义环境需要可选 environment.sh。

启动时自动加载所选 Geant4 的数据目录：若 geant4.sh 未导出变量，使用同目录 geant4-config --datasets 补齐。只使用存在的目录，不自动下载。数据环境补丁只更新 Bash 脚本，已编译用户可直接重试 make run-local；不要为此删除 runs/。
2. config/sim_config.json调物理/统计，run_config.json调任务分工与独立输出目录，cluster_config.json调资源/OS。
3. 在项目根目录执行：

```bash
make prepare
make submit
condor_q
```

4. 模拟结束后 `make submit-merge`；取回最终ROOT。

run_config字段：threads每作业线程1..18；jobs作业数且本批总核<=300；events_per_chunk落盘粒子数<=INT_MAX；master_seed正整数；output_directory相对runJSON目录。

cluster_config字段：request_memory_mb单模拟作业总内存；request_disk_mb磁盘资源；merge_memory_mb合并内存；target_os为auto/EL7/EL9；python_executable为计算节点Python绝对路径；requirements为额外单行筛选条件。EL9两项站点标记自动生成；EL7兼容站点标记或标准CentOS7/RedHat7字段。持续Idle时用condor_q -analyze核实。

模拟器输出在chunks；完整应用输出在logs/job_*_attempt_*.log；调度过程在scheduler.log。每次重试日志保留。submit本身也会记录返回的Cluster编号。

中断后先确认没有旧任务还在运行，再次make submit；完成块自动校验并跳过。只改资源申请可重新prepare生成提交文件；改物理/N/种子/划分则另开output_directory。

不要在登录节点make run-local。make all/prepare不提交模拟任务；make submit才提交。额外的大合并也走submit-merge。共享目录必须可被计算节点访问且支持flock。详细环境配置、恢复及SCP示例见 [总体手册](../MANUAL_CHN.md)。
