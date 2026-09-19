# cluster — user manual

```text
cluster/
├── prepare_jobs.py         # 配置冻结、分块清单与提交文件
├── workflow.py             # 本机/集群入口、日志、锁与信号
├── setup_env.sh            # 匹配编译环境的库及数据集
├── run_job.sh              # Python启动薄封装
├── simulation.sub.in       # 模拟作业模板
└── merge.sub.in            # 合并作业模板
```

After configuring the cluster environment and compiling, set physics/statistics in sim_config, partition/output in run_config and resources/OS in cluster_config. From the root:

```bash
make prepare
make submit
condor_q
```

After simulation completes, make submit-merge. Copy only final ROOT for plotting on the small server.

Dataset variables are restored from the selected Geant4 installation's sibling geant4-config --datasets when geant4.sh omits them. Only existing directories are exported, with no download or system modification. The dataset-env script patch does not require rebuilding an already compiled project or deleting runs/.

run_config fields: threads (1..18/job), jobs (campaign CPUs<=300), events_per_chunk (<=INT_MAX), positive master_seed, unique output_directory relative to the run JSON.

cluster_config fields: request_memory_mb (total/job), request_disk_mb, merge_memory_mb, target_os (auto/EL7/EL9), python_executable (absolute worker-visible Python), requirements (extra single-line selector). EL9 site markers are generated automatically; investigate Idle jobs with condor_q -analyze.

Chunks are in chunks/; combined application output is logs/job_*_attempt_*.log; scheduling history is scheduler.log. Each retry keeps a separate log. After confirming older jobs stopped, resubmit the same plan to skip verified chunks. Resource requests may be regenerated; changed physics/statistics/seed/partition requires a new output directory.

Never use run-local for production on a login node. all/prepare do not submit; submit does. Large merges use submit-merge. Shared storage must support cross-node flock. See the [main manual](../MANUAL.md) for environment, recovery and SCP steps.
