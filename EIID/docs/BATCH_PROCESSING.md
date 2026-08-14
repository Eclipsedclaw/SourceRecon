# EIID 生产批处理

## 隔离层级

- `logs/`：批启动日志和单数据集运行日志；
- `runs/<run_id>/`：结果、checkpoint、配置快照和 SUCCESS/FAILURE；
- `batch_runs/<batch_id>/`：批 manifest、内存遥测、子进程日志和失败清单；
- `response_campaign/`：离线响应输入与响应库。

所有路径必须位于 `/home/ezqi/labwork/SourceRecon/EIID`。

## 动态并发与恢复

`maximum_workers` 是上限，实际容量为：

    floor((available_memory - minimum_available) / estimated_worker_peak)

容量不足时不启动新数据集；内存跌破保留线时终止最近启动的 worker，记录
`memory_guard_terminated` 并按配置重试。每个 worker 的 BLAS/OpenMP 线程单独
限制，避免与数据集并行相乘。

只有 `SUCCESS.json` 才表示完成。`skip_completed=true` 按 dataset_id 跳过成功
结果；重试优先从完整 checkpoint 续跑并创建新 run_id，父目录永不覆盖。批结束
写 `failed_datasets.json` 以及批次 SUCCESS/FAILURE。

服务器 Bash 使用 `pipefail` 和 `tee -a`。子数据集输出同时进入主终端及
`batch_runs/<batch_id>/dataset_logs/`，Python 异常不会被 `tee` 掩盖。
