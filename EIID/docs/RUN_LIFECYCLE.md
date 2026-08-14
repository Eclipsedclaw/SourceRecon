# EIID 统一运行身份与生命周期

## 1. run_id

阶段 4 起，每次响应生产或重建都使用同一个 run_id 贯穿日志、运行结果和
响应 campaign。格式为：

    UTC微秒时间_运行类型_配置SHA256前8位_随机后缀

示例：

    20260807T092920835513Z_stage4_lmmlem_b8b96bbf_0cf006

配置哈希使用排序后的完整 JSON 配置快照计算。随机后缀避免同一微秒内并发
启动相同配置时发生冲突。

## 2. runs 目录

每次运行创建独立目录，已有 run_id 禁止静默覆盖：

    runs/<run_id>/
      run_manifest.json
      config_snapshot.json
      numerical/
        iteration_metrics.jsonl
        convergence_summary.json
      checkpoints/
      figures/
      SUCCESS.json 或 FAILURE.json

run_manifest 记录主机、PID、Python 版本、可执行文件、代码版本、配置哈希、
开始/结束时间、日志路径、运行状态和停止原因。

SUCCESS.json 最后原子写入。批处理调度器只能把存在有效 SUCCESS.json 的目录
视为已完成；只有目录或中间文件不能作为跳过依据。

## 3. logs 与 response_campaign

服务器包装器先生成 run_id，然后设置：

    EIID_RUN_ID=<run_id>
    EIID_LOG_PATH=<project>/logs/<run_id>.log

Python RunContext、终端 tee 和输出目录读取同一组环境变量。

响应原型库写入：

    response_campaign/response_library/<library_id>/<run_id>/

其中 manifest.json 保存 producer_run_id，SUCCESS.json 最后写入并绑定数组
SHA-256。响应库不再因重复运行同一示例而覆盖上一批结果。

## 4. 失败和中断

异常和 KeyboardInterrupt 会更新 run_manifest，并写入 FAILURE.json。失败标记
保存异常类型、信息、traceback 和停止原因；不会伪造 SUCCESS.json。

