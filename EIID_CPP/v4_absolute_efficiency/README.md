# EIID V4 Absolute-Efficiency Architecture

## 1. Purpose

V4 is a modular C++20 pipeline for Compton-camera direction–energy reconstruction. It keeps simulation, raw-data translation, grid resampling, reconstruction, and visualization independently compilable. The main physical change from V3 is that the detector calibration is now an **isotropic-point-source absolute detection-efficiency map** rather than a cone-conditional trigger ratio.

The source-direction sphere and reconstruction direction grid use the geometrical center of ch2 as their common reference point. The reconstruction kernel remains translation invariant because it uses `r2 - r1` and unit incident directions.

## 2. Architecture

```text
v4_absolute_efficiency/
├── common/                 Shared data model and HEALPix grid library
├── Reconstruction/         EIID response and LM-MLEM reconstruction
├── GridResampler/          Independent efficiency-grid adapter
├── Geant4_Simulation/      Dual-mode detector simulation
├── Translator/             Raw Geant4 Step → compact Event ETL
├── Visualization/          Independent ROOT plotting program
├── legacy_v3_snapshot/     Preserved copy of the inherited V3 layout
├── Makefile                Aggregate build entry
├── README.md               Developer documentation
└── MANUAL.md               User documentation
```

Dependency direction:

```text
Geant4_Simulation ──writes──> absolute_efficiency_master.root
                                      │
                                      v
                               GridResampler
                                      │
                                      v
                               absolute_efficiency.root
                                      │
events.root ──────────────────────────┼──> Reconstruction ──> result.root
                                      │                         │
                                      └─────────────────────────┘
                                                                v
                                                        Visualization

raw_steps.root ──> Translator ──> events.root
Geant4 mode 1 ──────────────────> events.root
```

No algorithm module depends on a concrete ROOT reader through hidden global state. Configuration and data objects are constructed in each `main.cpp` and injected explicitly.

## 3. Common library

`common/` builds `libeiid_common.a` and contains no ROOT or Geant4 code.

- `Common.h`: global `Decimal`, pi, and electron rest mass.
- `PhysicsTypes.h`: `Vec3`, compact `Event`, and direction–energy `Cell`.
- `IGrid.h`: abstract grid interface used by solvers and resamplers.
- `HealpixGrid.h/.cpp`: RING-order HEALPix direction grid plus linear energy grid.
- `AbsoluteEfficiencyMap.h/.cpp`: contiguous direction × energy storage with O(1) lookup, duplicate detection, range validation, and completeness checking.
- `EfficiencyFileSchema.h`: canonical ROOT Branch and metadata names shared by writer and readers.

The intended grid plug-in point is `IGrid`. A future grid implementation can be substituted without changing LM-MLEM.

## 4. Reconstruction module

`Reconstruction/` builds `EIID_Recon_V4`.

- `ReconConfig`: parses and validates `config/recon_config.json`; relative paths are resolved against the JSON directory.
- `IReconstructionSolver`: solver interface.
- `LmMlemSolver`: current list-mode MLEM implementation. Cells with efficiency `s_j <= 0` are forced to zero and are never used as divisors.
- `EiidResponse`: unchanged Compton energy/geometry consistency kernel.
- `RootEventReader`: reads only compact events (`r1`, `r2`, `e1`). It contains no Step aggregation.
- `RootEfficiencyReader`: reads the minimal efficiency Tree and verifies all grid and physics metadata.
- `RootImageWriter`: writes a self-describing direction–energy image for visualization.
- `main.cpp`: composition root; it creates config, grid, readers, solver, and writer.

The reconstruction solver depends on `IGrid` and `AbsoluteEfficiencyMap`, not on simulation classes.

## 5. GridResampler module

`GridResampler/` builds `grid_resampler`.

- `ResamplerConfig`: Master/Target grids, paths, and interpolation selection.
- `IInterpolationStrategy`: interpolation plug-in interface.
- `NearestInterpolation`: center-direction nearest-pixel mapping plus nearest energy point.
- `PolygonInterpolation`: common HEALPix refinement; micro-pixel counts approximate spherical overlap areas, followed by linear interpolation in energy.
- `GridAdapter`: owns Master and Target grids and chooses the requested strategy.
- `ResamplerIO`: reads/writes the same minimal absolute-efficiency schema and preserves source radius.
- `resampler_main.cpp`: independent composition root.

Adding another interpolation method only requires a new `IInterpolationStrategy` implementation and one factory branch in `GridAdapter`.

## 6. Geant4 simulation module

`Geant4_Simulation/` builds `geant4_simulator`.

### Geometry and source services

- `DetectorConstruction`: inherited detector construction, now with automatically sized World material and dimensions.
- `DetectorGeometryInfo`: single source of truth for ch2 center, trigger-envelope corners, and detector bounds.
- `ISourceGeometry`: source-position plug-in interface.
- `Ch2CenteredHemisphereSource`: places each point source at

  \[
  r_{source,j}=r_{ch2\ center}+R n_j.
  \]

- `IEmissionConePolicy`: directional importance-sampling interface.
- `AutoBoundingConePolicy`: points the cone at ch2 center and finds the maximum angle to the ch2+ch1 trigger-envelope corners, then adds a configurable safety margin.
- `AbsoluteEfficiencyEstimator`: converts the cone-conditional trigger fraction into the isotropic 4π probability:

  \[
  s_j=\frac{N_{valid,j}}{N_{cone,j}}\frac{1-\cos\alpha_j}{2}.
  \]

### Geant4 actions and I/O

- `SimulationGrid`: maps Geant4 event IDs to HEALPix direction–energy cells.
- `PrimaryGeneratorAction`: uses injected source and cone policies and samples uniformly in cone solid angle.
- `EventAction`: energy-weighted hit aggregation and ch2+ch1 trigger decision.
- `RunAction`: owns counters and delegates output to `RootWriter`.
- `RootWriter`: Mode 0 writes the absolute-efficiency map; Mode 1 writes compact triggered events.
- `TrackerHit/TrackerSD`, `MyPhysicsList`, and messenger classes: inherited Geant4 detector support.
- `main.cpp`: constructs all services and injects them into Geant4 actions.

The source placement, emission-cone calculation, and absolute-efficiency normalization are separate classes and can be replaced independently.

## 7. Translator module

`Translator/` builds `eiid_translator`.

- `IoConfig`: JSON path, branch, chamber, and threshold configuration.
- `root_simulation_translator`: streaming state machine grouped by `eventID`; positive-energy Steps are merged by chamber using an energy-weighted centroid.
- Trigger policy requires ch2 (`chamberID 0`) and ch1 (`chamberID 1`).
- The output order is fixed: `r1/e1 = ch2`, `r2 = ch1`.
- `translate_main.cpp`: independent executable entry.

The Translator is optional when Geant4 mode 1 already writes compact events.

## 8. Visualization module

`Visualization/` builds `eiid_plotter` and preserves the existing plotter polymorphism.

- `IPlotter`: plot plug-in interface.
- `SkymapPlotter`: full-sky heat map with camera front (`-Z`) at display center.
- `SpectrumPlotter`: direction-marginalized energy spectrum.
- `ContainmentPlotter`: cumulative angular containment and R50/R68/R90.
- `VisConfig`: plot and truth JSON reader.
- `ReconstructionDataReader`: reads `result.root` once for all plotters.
- `PlotUtils`: shared coordinate and binning functions.
- `vis_main.cpp`: selects plotters from JSON switches.

## 9. ROOT schemas

### Absolute efficiency file

Tree name is configurable; the default is `Sensitivity`.

Branches:

- `cell_index` (`ULong64_t`)
- `sensitivity` (`Double_t`)

Mandatory file-level metadata:

- `healpix_nside`
- `healpix_ordering = RING`
- `direction_count`
- `energy_count`
- `energy_min_MeV`
- `energy_max_MeV`
- `source_radius_mm`
- `efficiency_definition = isotropic_point_source_absolute_detection_efficiency_4pi`

### Compact event file

Default Tree: `Events`.

Branches: `eventID`, `source_cell_index` (direct Geant4 mode only), `r1_x/y/z`, `r2_x/y/z`, and `e1_MeV`. The Translator output omits `source_cell_index`, which reconstruction does not require.

### Reconstruction result

Default Tree: `EiidImage`. It stores cell index, weight, HEALPix pixel ID, theta, phi, Cartesian direction, and energy.

## 10. Builds and extension rules

Every top-level module has its own `Makefile`; the root `Makefile` only delegates. A module may be built from its own directory without compiling unrelated executables. `Reconstruction` and `GridResampler` automatically build `common` when needed.

When extending V4:

1. Depend on interfaces, not concrete implementations.
2. Keep ROOT ownership inside I/O classes.
3. Keep Geant4 actions free of output-file lifecycle management.
4. Resolve user paths relative to the JSON file, not the current shell directory.
5. Update both the module README/MANUAL and the root documents when schemas or parameters change.
6. Never silently accept mismatched grid metadata.

The inherited V3 files are preserved under `legacy_v3_snapshot/` for audit only and are not part of any V4 build target.

## 11. Machine-local dependency configuration

`configure.sh` is the single dependency-discovery entry point. It locates ROOT, HEALPix, nlohmann/json, and optionally Geant4 from known project/environment prefixes, `PATH`, the user's home directory, `/opt`, or `/usr/local`. Known dependency prefixes are checked before PATH so that an incompatible Snap ROOT cannot hide the project's ROOT/HEALPix environment. For shared Geant4 installations it compares all candidates, ignores `*-build` trees, and selects the highest installed version. Explicitly supplied `ROOT_CONFIG` and `GEANT4_CONFIG` values remain authoritative. It writes absolute machine-local paths to `config/local.mk`.

Every module Makefile includes that file. No module relies on an activated Conda shell or an implicit `CONDA_PREFIX`. Link targets also consume `EIID_RPATH_FLAGS`, so the resulting executables retain the discovered shared-library search paths.

`config/local.mk` is machine-specific and must be regenerated after moving the project to another server. `config/local.mk.example` documents its schema. `PROJECT_CXX_STANDARD := c++20` is the single language-standard setting. Module Makefiles remove any `-std=...` supplied by ROOT or Geant4 and append this project setting last, preventing an old dependency from silently downgrading the build. Dependency discovery changes only the build configuration; it does not modify C++ source, physics parameters, or ROOT schemas.
