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

`inputs[]` 可放两个以上结果，每项设置 `label`、`kernel_type`、`file` 和 `tree`；另设 `truth_info_file`、`output_json`、`figures_directory`。比较前必须保证这些结果来自同一事件、效率、网格和迭代设置。
