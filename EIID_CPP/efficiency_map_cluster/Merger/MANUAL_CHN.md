# Merger：操作说明

```text
Merger/
├── include/CountMerger.h
├── src/CountMerger.cpp
├── src/main.cpp
└── CMakeLists.txt
```

本机小数据合并（项目根目录）：

```bash
make merger
make merge
```

cluster大数据请执行 `make submit-merge`，在计算节点合并。

`make check`只检查所有分块；如果最终ROOT已存在也检查其内容，不新建最终文件。已有完整最终文件再次merge会验证并保留。

没有单独的merge_config.json，合并输入由run_config.output_directory指定批次里的manifest.json决定。换批次：

```bash
make merge RUN_CONFIG=config/my_run.json
```

独立编译只需ROOT：

```bash
cmake -S Merger -B build-merger -DCMAKE_PREFIX_PATH=/实际ROOT前缀
cmake --build build-merger --parallel 4
```

加载该ROOT环境后直接接口是 `build-merger/bin/efficiency_merge /绝对路径/manifest.json [--check-only]`；方括号表示可选，不要原样输入。直接运行没有自动日志，统一make包装命令有。

最终产物位于批次根目录raw_efficiency_master.root；日志在logs/merge_attempt_*.log。输入错误先看日志，不要用hadd代替：本项目分块可能包含同一个cell，必须相加计数后计算效率，而不是拼接重复行。

