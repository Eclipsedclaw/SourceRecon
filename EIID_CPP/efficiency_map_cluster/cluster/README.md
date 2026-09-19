# cluster — developer guide

```text
cluster/
├── prepare_jobs.py         # 配置冻结、分块清单与提交文件
├── workflow.py             # 本机/集群入口、日志、锁与信号
├── setup_env.sh            # 匹配编译环境的库及数据集
├── run_job.sh              # Python启动薄封装
├── simulation.sub.in       # 模拟作业模板
└── merge.sub.in            # 合并作业模板
```

A standard-library Python/Bash orchestration layer, with no physics or plotting.

prepare_jobs freezes configuration, validates uint64 scale and creates contiguous event blocks assigned by block_id%jobs. Repreparation preserves campaign identity only for the same plan.

workflow captures combined stdout/stderr bytes, tees output to unique per-attempt logs, holds an OS lock per job and forwards TERM/INT/HUP to the child process group. Kill/power-loss diagnostics also require scheduler logs.

setup_env loads machine-local configuration and CMake-selected runtime libraries/data. Condor uses shared storage, no file transfer, and request_cpus matches workers. Merger content checks run on a compute node; submit-merge only checks that expected filenames exist before submission.

