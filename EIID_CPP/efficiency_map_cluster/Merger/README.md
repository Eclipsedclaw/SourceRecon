# Merger — developer guide

```text
Merger/
├── include/CountMerger.h
├── src/CountMerger.cpp
├── src/main.cpp
└── CMakeLists.txt
```

CountMerger reads only manifest-listed chunks, validates identity/software and exact event/cell coverage, and sums uint64 counters. Unknown ROOT files are rejected; temporary files are ignored; genuine zeros are allowed.

Only after merging is efficiency computed as sum(valid)/sum(emitted)*cone_fraction. Averaging efficiencies or concatenating duplicate rows is incorrect. common's RootCountsIO writes full-sky RawEfficiency and metadata, or verifies an existing final file row-by-row.

ROOT/common are the only dependencies. Upstream: Simulation chunks. Downstream: existing small-server Quicklook.

