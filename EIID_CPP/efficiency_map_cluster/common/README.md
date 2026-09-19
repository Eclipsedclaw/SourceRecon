# common — developer guide

```text
common/
├── include/SimulationConfig.h / ConfigManager.hh
├── include/TaskSpec.h / CellCounts.h / RootSchema.h
├── src/SimulationConfig.cpp / TaskSpec.cpp / CellCounts.cpp
├── io/RootCountsIO.cpp
└── CMakeLists.txt
```

SimulationConfig validates read-only physics settings; ConfigManager.hh preserves the detector's legacy class interface. Campaign reads frozen manifests, validates exact global ranges, names chunks and constructs identity records. CellCounts implements uint64 counters, overflow-safe addition and coverage checks.

eff_common has no ROOT dependency. The separate eff_root_io implements temporary-file publication, ROOT readback and final RawEfficiency serialization. Upstream: JSON/manifest. Consumers: Simulation and Merger. A schema change must update both and the existing Quicklook.

eff_root_io publicly links ROOT::TreePlayer and eff_runtime so all ROOT consumers inherit identical linkage/runtime selection. The parent cmake/CheckDependencies.cmake validates the real libraries; physics functions do not manage environments.
