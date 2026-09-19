# Geant4_Simulation — Developer README

This independently compiled Geant4 program has two modes: absolute-efficiency calibration and direct compact-event generation.

## Object boundaries

- `ConfigManager`: JSON parsing only.
- `DetectorConstruction`: detector and automatically sized World.
- `DetectorGeometryInfo`: shared geometry facts; ch2 center and trigger-envelope corners are calculated once.
- `ISourceGeometry` / `Ch2CenteredHemisphereSource`: source-location plug-in.
- `IEmissionConePolicy` / `AutoBoundingConePolicy`: importance-sampling plug-in.
- `AbsoluteEfficiencyEstimator`: Jeffreys-regularized cone probability and 4π normalization.
- `SimulationGrid`: eventID-to-cell mapping.
- `PrimaryGeneratorAction`: particle creation using injected source/cone services.
- `EventAction`: hit aggregation and trigger decision.
- `RunAction`: counter lifecycle and output delegation.
- `RootWriter`: the only class that owns ROOT output files.
- `TrackerHit`, `TrackerSD`, `MyPhysicsList`, and detector messenger: inherited Geant4 support.

## Physical reference

HEALPix vector `n_j` points from the ch2 geometrical center toward the point source. The incident central ray is `-n_j`. The source is placed at `ch2Center + R*n_j`.

`AutoBoundingConePolicy` encloses the axis-aligned bounding volume containing the ch2 and ch1 active YSO layers. Its half-angle is the largest source-to-corner angle plus a safety margin. Sampling is uniform in cone solid angle.

For Mode 0:

```text
absolute efficiency = (valid + 0.5) / (cone-emitted + 1)
                      × (1 - cos(half-angle)) / 2
```

For a simulated cell, `valid = 0` now produces a small positive estimate instead of a false hard veto. `cone-emitted = 0` identifies a cell outside the configured domain and remains exactly zero. The correction vanishes at high statistics.

Only `cell_index` and `efficiency` are stored per cell. Scientific/grid metadata is stored once at file level.

## Extension points

Alternative source distributions implement `ISourceGeometry`. Alternative importance samplers implement `IEmissionConePolicy`. They can be injected in `main.cpp` without modifying Geant4 actions or ROOT output.

The standalone Makefile reads ROOT, HEALPix, JSON, Geant4, and rpath settings from `../config/local.mk`. If Geant4 is absent, `configure.sh` still configures the other modules and this module alone reports the missing dependency.

For shared installations, dependency discovery compares every candidate from PATH, HOME, `/opt`, and `/usr/local`, rejects CMake `*-build` trees, and selects the highest installed Geant4 version. External `-std=...` flags are stripped and the project-wide C++20 setting is appended last.
