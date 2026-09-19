# Efficiency Map Cluster — developer guide

Standalone raw-efficiency generation derived from the corrected serial raw_efficiency_map_experiment. This is not a new reconstruction version. Historical projects are untouched. The program produces ROOT data, not events.root or plots.

See [MANUAL.md](MANUAL.md) for operation and [README_CHN.md](README_CHN.md) / [MANUAL_CHN.md](MANUAL_CHN.md) for Chinese documentation.

## Structure

```text
efficiency_map_cluster/
├── config/               # sim_config, run_config, cluster_config, environment example
├── common/
│   ├── include/          # ConfigManager, Campaign, CellCounts, ROOT protocol
│   ├── src/              # validation, uint64 indexing/count arithmetic
│   └── io/RootCountsIO.cpp
├── Simulation/
│   ├── include/          # OOP source/cone interfaces and Geant4 actions
│   └── src/              # original geometry/physics + MT orchestration
├── Merger/
│   ├── include/CountMerger.h
│   └── src/              # count-based merge and separate entry point
├── cluster/              # immutable plans, HTCondor templates, logging, retries
├── tests/                # fixed fixtures; counts, ROOT roundtrip, workflow tests
├── third_party/          # nlohmann/json 3.11.3 and license
├── cmake/
│   ├── DiscoverDependencies.cmake
│   ├── CheckDependencies.cmake / dependency_probe.cpp
│   └── BuildInfo.h.in
├── CMakeLists.txt / Makefile / configure.sh
├── README.md / README_CHN.md / MANUAL.md / MANUAL_CHN.md
└── runs/<campaign>/      # created at runtime, excluded from distribution
    ├── manifest.json / submission_info.json
    ├── simulation.sub / merge.sub
    ├── chunks/chunk_*.root
    ├── logs/ / .locks/
    └── raw_efficiency_master.root
```

JSON → frozen manifest → independent jobs × Geant4 worker threads → integer-count chunks → checked merge → final ROOT → SCP to the small server's existing Quicklook.

## Ownership and extensibility

ConfigManager retains the serial class name to reuse detector construction. Campaign owns immutable configuration and range metadata; RunContext is modified only by the master between BeamOn calls.

ISourceGeometry and IEmissionConePolicy isolate source placement and directional sampling geometry. Their present implementations are Ch2CenteredHemisphereSource and AutoBoundingConePolicy. The detector geometry, TrackerSD energy handling and Livermore physical list are inherited. No full-absorption cut is added.

ActionInitialization builds a separate gun, EventAction and RunAction for every worker. EfficiencyRun owns thread-local sparse integer counts and implements G4Run::Merge. Workers never write ROOT; the master validates and publishes one chunk after each completed BeamOn.

The common counting library has no ROOT dependency. eff_root_io provides ROOT persistence separately. Merger uses these two libraries but does not link Geant4 or HEALPix. Python orchestration uses only the standard library.

## Physical contract

A cell is a HEALPix direction center and an incident energy point. Source position is ch2 center + radius × direction. The cone covers the existing trigger envelope and is sampled uniformly in solid angle. ch2=0 and ch1=1 must each exceed the energy threshold; gamma escape is allowed.

Raw isotropic point-source efficiency is:

```text
N = sum(emitted_count)
k = sum(valid_count)
f = (1 - cos(cone_half_angle)) / 2
efficiency = (k/N) * f
```

No smoothing or positive floor is applied. Simulated zero-count cells remain zero; unsimulated cells have N=0 and remain distinguishable.

The 4π conversion assumes excluded emission directions cannot contribute accepted triggers. The default vacuum and trigger envelope reproduce the prior experiment. Air, surrounding scattering material, or paths via downstream backscatter may require a larger validated envelope; multiplying by f cannot restore omitted paths. This is efficiency for the specified detector model, not automatically a fully calibrated real-instrument efficiency.

## Parallel/restart contract

- Total events do not depend on thread/job counts. uint64 global IDs map to cells; each BeamOn remains within INT_MAX.
- SplitMix64 mixes the master seed and global event ID into Ranecu seeds. Sampling is independent of worker assignment; cross-version/compiler bitwise reproducibility is not promised.
- Completed chunks carry identity, configuration, source hash, compiler/dependency versions and dataset paths. Mixed campaigns/software are rejected.
- Chunk writes use a temporary file, actual ROOT readback, then same-filesystem rename. Temporary files are ignored; completed chunks are verified and skipped on retry.
- Merge checks exact event coverage, cell counts, expected files and metadata, then sums integers. It never averages already-computed efficiencies.
- Existing final ROOT is checked row-by-row, not silently overwritten.
- The runtime wrapper holds an OS file lock and writes a unique combined stdout/stderr log for every attempt. Shared storage must support cross-node flock.

## ROOT protocol

ChunkCounts tree: cell_index, emitted_count, valid_count, hit_count, front_count, rear_count (ULong64_t), cone_solid_angle_fraction (Double_t). chunk_metadata is a TNamed JSON record with identity, software and complete=true.

RawEfficiency tree: cell_index, emitted_count, valid_count (ULong64_t), efficiency and cone_solid_angle_fraction (Double_t). All sky cells are written. cell_index = direction_index * energy_count + energy_index, with HEALPix RING ordering.

Metadata: healpix_nside, healpix_ordering, direction_count, energy_count, energy_min_MeV, energy_max_MeV, source_radius_mm, efficiency_definition, requested_event_count_u64 (decimal string), campaign_metadata (JSON). This supports the existing raw Quicklook without copying intermediate chunks.

## Dependencies and verification

CMake >=3.20; a Linux C++17 compiler; ROOT >=6.28; Geant4 >=11.2 built with multithreading and shared libraries; HEALPix C++; Python >=3.8. The language standard is raised when dependencies require C++20. ROOT::TreePlayer is required by TTreeReader and may pull in ROOT graphics libraries transitively; no GUI application, plot or Geant4 Qt/OpenGL driver is created.

DiscoverDependencies searches explicit, active and bounded known prefixes. CheckDependencies performs actual compile/link/startup checks before accepting a configuration. If default linking fails, ROOT's own libstdc++.so.6 is tried and used only if the checks pass. eff_runtime propagates the chosen runtime to all consumers of eff_root_io; ROOT::TreePlayer is also a PUBLIC dependency there. Linux checks actual loaded Core/G4run/runtime locations and unresolved symbols with ldd -r. configure.ok is published only after generation succeeds; configure.sh removes it on failure and preserves diagnostic logs. No particles are simulated by this probe.

See VALIDATION.md for what has actually been tested. The delivery machine lacks ROOT/Geant4, so a real MT transport smoke test remains necessary.

The dependency probe calls the out-of-line G4RunManager::GetRunManager() query to exercise G4run without initializing a simulation. Never construct a standalone G4Run in this probe: in Geant4 11.2.2 its destructor dereferences the current run manager. The old probe violated this lifecycle requirement, as confirmed by the test5 crash stack. Production TaskRunner creates and owns a G4MTRunManager before executing events; its physics code is unchanged by this fix.

Each module has its own English/Chinese developer and user guides. The JSON dependency is pinned to 3.11.3 with its license.

cluster/setup_env.sh uses the selected installation's geant4-config --datasets to restore valid dataset directories when geant4.sh omits their environment variables. The query uses an exact sibling path, not PATH lookup or eval. tests/test_dataset_environment.py exercises this environment orchestration with temporary fixtures; it does not emulate physics libraries.

References: [INPAC HTCondor](https://inpac.sjtu.edu.cn/cluster-help/px/condorquickguide.html), [shared filesystem](https://inpac.sjtu.edu.cn/cluster-help/px/filesystem.html), [Geant4 MT design](https://geant4.web.cern.ch/documentation/pipelines/master/bftd_html/ForToolkitDeveloper/OOAnalysisDesign/Multithreading/mt.html).
