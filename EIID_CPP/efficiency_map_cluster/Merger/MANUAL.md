# Merger — user manual

```text
Merger/
├── include/CountMerger.h
├── src/CountMerger.cpp
├── src/main.cpp
└── CMakeLists.txt
```

For small local datasets, from project root: make merger, then make merge. For cluster-scale data, make submit-merge runs on a compute node. make check validates all chunks and any existing final output without creating a new final ROOT.

There is no separate merge JSON: run_config.output_directory selects a frozen manifest. Alternate batch: make merge RUN_CONFIG=config/my_run.json.

Standalone ROOT-only build:

```bash
cmake -S Merger -B build-merger -DCMAKE_PREFIX_PATH=/actual/ROOT/prefix
cmake --build build-merger --parallel 4
```

After loading ROOT: build-merger/bin/efficiency_merge /absolute/path/manifest.json, optionally followed by --check-only. Direct execution does not auto-log; unified workflow commands do.

Final output is raw_efficiency_master.root in the campaign directory; logs are logs/merge_attempt_*.log. Do not replace the merger with hadd: cells can span chunks and require count summation, not duplicate row concatenation.

