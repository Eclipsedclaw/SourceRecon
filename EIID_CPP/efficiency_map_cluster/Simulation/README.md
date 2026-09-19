# Simulation — developer guide

Independent efficiency_simulator: Geant4 event-level multithreading only; no reconstruction, event conversion or plotting.

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

TaskRunner selects unfinished manifest tasks and controls BeamOn boundaries. ActionInitialization creates per-worker actions and master-only RunAction. SimulationGrid maps global events to cells. PrimaryGeneratorAction explicitly selects gamma, seeds each global event and caches source/cone geometry per cell.

EventAction sums all positive chamber deposits and applies the two-layer threshold without requiring full absorption. EfficiencyRun owns local counts and merges them; master RunAction validates and writes chunks. Registered actions/runs are owned by Geant4.

Source and cone policies are replaceable interfaces. Read-only detector geometry/configuration is shared; hits, guns and counters are thread-local. No worker accesses ROOT output. The inherited corrected detector/SD/physics definitions remain the physical baseline.

