# Simulation — user manual

```text
Simulation/
├── include/
│   ├── TaskRunner.hh / ActionInitialization.hh
│   ├── EfficiencyRun.hh / RunAction.hh / EventAction.hh
│   ├── PrimaryGeneratorAction.hh / SimulationGrid.hh
│   ├── ISourceGeometry.hh / IEmissionConePolicy.hh
│   ├── Ch2CenteredHemisphereSource.hh / AutoBoundingConePolicy.hh
│   └── DetectorGeometryInfo、DetectorConstruction、TrackerHit/SD、MyPhysicsList等
├── src/                       # 对应实现，含 main.cpp
└── CMakeLists.txt
```

From the project root, configure dependencies and build (prefer make all initially, since run-local also merges):

```bash
make configure
make all
make run-local
```

A single logged job can be retried with:

```bash
python3 cluster/workflow.py job --manifest runs/smoke_001/manifest.json 0
```

The last argument is job_id. Submit cluster work through make submit, not direct login-node execution.

Independent build: cmake -S Simulation -B build-simulation, then cmake --build build-simulation --parallel 4. Requires ROOT, Geant4>=11.2 MT and HEALPix. Binary: build-simulation/bin/efficiency_simulator. Load matching runtime libraries/data before direct use; unified wrappers use build/bin.

sim_config controls source radius/hemisphere/cone margin, World material/padding, Nside, incident energy grid, per-cell statistics and trigger threshold. Keep gamma and chamber0/1. run_config controls threads, jobs, chunk size, seed and unique output directory. See the [complete reference](../MANUAL.md).

Inspect actual gamma and emitted/hit/front/rear/valid counters. A positive-trigger smoke run is required before production. Completed chunks are validated and skipped on retry; incomplete chunks are recomputed. No plots or events.root are produced.

