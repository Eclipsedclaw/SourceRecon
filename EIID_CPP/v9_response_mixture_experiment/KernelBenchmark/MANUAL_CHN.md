# KernelBenchmark——用户手册

## 目录和运行

```text
config/  输入结果与真值
output/  JSON 指标
figures/ 叠图
```

```bash
cd KernelBenchmark
make
./kernel_benchmark config/benchmark_config.json
```

或在根目录执行 `make benchmark`。

`inputs[]` 列出全部候选结果，每项设置 `label`、`kernel_type`、`file` 和 `tree`；另设：

- `model_status_json`：标定器生成的模型可用性清单；不可用模型自动跳过。
- `calibration_comparison_json`：读取相同留出测试集的 NLL 与 AIC/BIC。
- `truth_info_file`：统一真值。
- `output_json`：数值指标与跳过原因。
- `figures_directory`：模型叠图目录。

比较前必须保证所有结果来自同一外部事件、效率图、网格和迭代设置。输出同时包含 `calibration_test_nll_per_event` 与最终重建指标，但不把不同单位强行合成单一总分。推荐在根目录执行 `make benchmark`；默认结果写入 `runs/latest/benchmark/`。
