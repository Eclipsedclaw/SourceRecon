# common — user manual

```text
common/
├── include/SimulationConfig.h / ConfigManager.hh
├── include/TaskSpec.h / CellCounts.h / RootSchema.h
├── src/SimulationConfig.cpp / TaskSpec.cpp / CellCounts.cpp
├── io/RootCountsIO.cpp
└── CMakeLists.txt
```

No standalone transport executable is provided. From the project root:

```bash
cmake -S common -B build-common
cmake --build build-common --parallel 4
ctest --test-dir build-common --output-on-failure
```

This pure counting build requires no ROOT/Geant4. Unified make test additionally tests actual ROOT persistence when ROOT is available.

Edit config/sim_config.json, not generated manifests. Radius/hemisphere/cone margin define source sampling; Nside and energy endpoints/count define the grid; particles_per_cell defines statistics; layer thresholds define acceptance. See [full parameter reference](../MANUAL.md#configuration-reference).

A simulated k=0 cell must remain zero, while an unsimulated cell has N=0. This module does not regularize efficiencies. New physics or partitioning requires a new campaign directory.

