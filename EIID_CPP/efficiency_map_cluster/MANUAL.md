# Efficiency Map Cluster — user manual

Generate raw efficiency data on the cluster; copy the final ROOT file to the small server for plotting. No events.root input or reconstruction is involved.

## Two-stage operation

### Small-server smoke test

Upload the source folder and enter it. Normally no environment.sh is needed: configure searches active/known root-env prefixes and bounded /opt Geant4 installation paths. environment.sh is an optional override for a specific group toolchain; preserve an existing file. Copying the commented example alone does not activate an environment.

```bash
make configure &&
make all &&
make test &&
make run-local
```

Defaults: Nside2, one 0.662 MeV energy, 28 front-hemisphere directions, 10000 particles per cell, total280000 events. Two local jobs run sequentially, each with4 worker threads, producing four chunks. Check for positive two-layer trigger counts and successful merging. This verifies the processing path, not precise physical efficiency.

Output: runs/smoke_001/raw_efficiency_master.root. Logs: runs/smoke_001/logs/. make smoke builds incrementally and then runs locally; configure is still required first.

### Cluster production

Upload sources only, not local build directories, binaries, environment.sh or existing runs. Use group-provided shared storage visible to worker nodes. Compile against dependencies compatible with the selected worker OS. Use the optional environment.sh only if discovery misses a custom installation or a specific group toolchain must be loaded:

```bash
make configure
make all
```

Increase statistics in sim_config.json; adjust run/cluster settings below. Use a NEW output_directory, such as ../runs/production_001.

```bash
make prepare
make submit
condor_q
```

After all simulation jobs finish:

```bash
make submit-merge
condor_q
```

Merge runs on a compute node too. Do not use run-local or run a large simulator directly on a cluster login node.

## Configuration reference

All relative output paths are resolved from the run JSON's directory, not the terminal working directory.

### config/sim_config.json

| Field | Meaning |
|---|---|
| source.particle_name | Must be gamma; explicitly overrides the particle gun's default |
| source.hemisphere_radius_mm | Source distance from ch2 center, mm, positive; default5000 |
| source.front_hemisphere_only | true: source directions z<=0 including equator; false: full sphere |
| source.emission_cone_safety_margin_degree | Extra half-angle added to the automatic envelope, degrees, [0,45), default1 |
| environment.world_material | G4_Galactic vacuum (default) or G4_AIR; air requires reconsidering contributions excluded by the cone |
| environment.world_margin_mm | Positive World padding beyond source sphere/detector, mm |
| grid.healpix_nside | Power of two, 1..8192; controls directional resolution and memory |
| grid.energy_point_count | Number of incident energy sample points, positive |
| grid.energy_min_MeV | Positive lower energy endpoint |
| grid.energy_max_MeV | Upper endpoint; must equal min for one point, exceed min for multiple points |
| grid.particles_per_cell | Total emitted particles per active direction–energy cell; uint64, not per thread |
| trigger.front_chamber_id | Keep0 (ch2), fixed to inherited geometry |
| trigger.rear_chamber_id | Keep1 (ch1), fixed to inherited geometry |
| trigger.minimum_layer_energy_MeV | Both layer energy sums must separately exceed this nonnegative threshold |

Energy points are uniformly spaced including both endpoints. Full-sky direction count=12*Nside²; front hemisphere including equator=6*Nside²+2*Nside. Total events=active directions*energy points*particles_per_cell.

Nside16,50energies,100000/cell already means7.84billion events. Estimate duration from a pilot run. Use a single energy0.662 if only that slice is needed.

### config/run_config.json

| Field | Meaning |
|---|---|
| threads | Geant4 workers per job,1..18; becomes request_cpus |
| jobs | Number of jobs; this template limits jobs*threads<=300 and jobs<=chunks |
| events_per_chunk | Events in one BeamOn/checkpoint,1..2147483647; cells can span chunks |
| master_seed | Positive integer controlling globally indexed event seeds |
| output_directory | Unique campaign directory, relative to this JSON's directory |

Threads/jobs redistribute the same total events. Smaller chunks reduce retry loss but add overhead. Default70000 is for the smoke run; start production with a measured chunk duration. Consider8threads×16jobs=128cores, while accounting for your other jobs.

Changing physics, statistics, seeds or partitioning after preparation requires a new output directory. The manifest is a frozen snapshot, not a live view of editable config files.

### config/cluster_config.json

| Field | Meaning |
|---|---|
| request_memory_mb | Total memory requested per simulation job, MB |
| request_disk_mb | Per-job disk resource request, MB; shared filesystem quota is separate |
| merge_memory_mb | Memory requested for the merger |
| target_os | auto, EL7 or EL9; must match build/dependency OS |
| python_executable | Absolute worker-visible Python >=3.8 executable, default /usr/bin/python3 |
| requirements | Optional additional single-line HTCondor requirement expression |

EL9 generates both site-required OS selection fields. EL7 accepts the site attribute or standard CentOS7/RedHat7 OS attributes. Investigate persistent Idle status with condor_q -analyze. Do not send EL9 binaries to EL7.

The template follows the site limit of18CPUs/job and conservatively caps this campaign at300CPUs. This does not account for other campaigns under your account.

### config/environment.sh

Optional: source a specific compiler/ROOT/Geant4-MT/HEALPix environment and set CMAKE_PREFIX_PATH where needed. It is not required when automatic discovery succeeds. Example paths must be checked, not blindly copied to the cluster.

configure generates build/runtime_paths.sh from selected libraries. The runtime wrapper prepends those paths and reloads the selected geant4.sh data environment. Do not mix old Geant4 data with newer libraries.

If geant4.sh does not export dataset variables, setup_env.sh queries geant4-config --datasets from that same bin directory and exports existing directories as a fallback. Valid paths provided by the selected setup script are retained; missing directories are reported, not fabricated or downloaded. The dataset-env incremental patch requires no C++ rebuild on an already configured and built installation: apply it from the project parent, then run make run-local. It preserves user JSON, environment.sh, binaries and results.

Configure compiles, links and starts an in-memory ROOT TreePlayer/HEALPix/Geant4-library probe, without particle transport or efficiency output. The Geant4 check calls G4RunManager::GetRunManager() without constructing an orphan G4Run. On Linux it also checks actual library paths and unresolved symbols using ldd -r. If default linking fails, ROOT's adjacent libstdc++.so.6 is tested; it is used only after successful checks. No system libraries are replaced. Logs: build/configure_TIMESTAMP_PID.log and build/dependency-check.log. A failed configuration cannot authorize make all/run-local merely because CMakeCache.txt exists.

For a custom runtime, pass -DEFF_CXX_RUNTIME_LIBRARY=/compatible/path/libstdc++.so.6; the same checks remain mandatory. To change compilers, rename the old build directory for safekeeping before using CXX=/actual/compiler make configure. Never delete runs for a build fix. Changing -std=c++17/20 does not fix missing GLIBCXX/CXXABI symbols. Arbitrary dependency/OS combinations are not guaranteed compatible.

Probe stages are flushed to `build/dependency-check/probe.stderr.log` during execution. Linux library checks run before the probe. A timeout reports the last stage instead of claiming compiler incompatibility. `make configure CMAKE_ARGS="-DEFF_PROBE_TIMEOUT_SECONDS=120"` changes the cached timeout (default 45 seconds, range 1–600); it does not bypass validation or fix an unexplained hang. Normal exit is required even after the final main-function marker. The subsequent test5 log identified a G4Run destructor crash caused by the old probe's missing run manager. Apply efficiency_map_cluster_g4run_probe_fix.zip from the project parent directory, then rerun make configure; no clean or physics configuration change is required.

## Command reference

| Action | Command |
|---|---|
| Configure dependencies | make configure |
| Build everything | make all |
| Build simulator only | make simulation |
| Build merger only | make merger |
| Software tests, no large transport | make test |
| Prepare/freeze plan only | make prepare |
| Local simulation and merge, with logs | make run-local |
| Submit simulation jobs | make submit |
| Submit merge job | make submit-merge |
| Local validation, no new final output | make check |
| Local merge, or verify existing final ROOT | make merge |

run-local does not compile. Changing JSON requires no compilation but requires a new campaign if the frozen plan changes.

Alternate configurations:

```bash
make prepare SIM_CONFIG=config/my_sim.json RUN_CONFIG=config/my_run.json CLUSTER_CONFIG=config/my_cluster.json
make submit SIM_CONFIG=config/my_sim.json RUN_CONFIG=config/my_run.json CLUSTER_CONFIG=config/my_cluster.json
make submit-merge RUN_CONFIG=config/my_run.json
```

Always pass the matching RUN_CONFIG. Retry one local job with logging:

```bash
python3 cluster/workflow.py job --manifest runs/smoke_001/manifest.json 0
```

Low-level executables accept manifest and job ID, not the sim JSON:

```bash
bash cluster/setup_env.sh build/bin/efficiency_simulator runs/smoke_001/manifest.json 0
bash cluster/setup_env.sh build/bin/efficiency_merge runs/smoke_001/manifest.json --check-only
```

Low-level direct execution does not automatically tee output; prefer wrappers.

## Logs and recovery

Application logs are logs/job_0000_attempt_TIMESTAMP_UNIQUE.log, with combined stdout/stderr, host, command, start/end, exit status, selected software/config and chunk counters. Every attempt is retained. scheduler.log and Condor .out/.err preserve scheduling and launcher diagnostics.

Power loss or SIGKILL can prevent a final buffered message/end marker. Inspect scheduler logs; file presence is not success.

Before resubmitting, confirm no older jobs for this campaign remain running. Verified chunks are skipped; interrupted blocks are recomputed, not partially resumed. Temporary files are ignored.

Move a corrupt completed chunk outside chunks for safekeeping, then retry its assigned job. An unexpected .root inside chunks is deliberately rejected. If only the final file is corrupt, move it aside and rerun merging without deleting chunks.

All-zero raw counts are allowed, with a warning. Check actual gamma, detector-hit and layer counters before scaling up an all-zero smoke run.

## Copy back and plot

SCP only the final raw_efficiency_master.root to the small server; copy logs too for debugging. Existing raw Quicklook can read the final metadata/schema.

For a file placed at /home/ezqi/raw_efficiency_master.root on the small server:

```bash
cd ~/labwork/SourceRecon/EIID_CPP/raw_efficiency_map_experiment/Quicklook
root -l -b -q 'run_raw_efficiency_map.C("/home/ezqi/raw_efficiency_master.root","cluster_figures")'
```

This selects0.662MeV and uses the existing rectangular/skymap renderer. Full-sphere simulations require the old Quicklook's hemisphere-display setting to match; this project does not edit that tool.

## Independent builds and manual dependency selection

```bash
cmake -S common -B build-common
cmake --build build-common --parallel 4
cmake -S Merger -B build-merger -DCMAKE_PREFIX_PATH=/actual/ROOT/prefix
cmake --build build-merger --parallel 4
cmake -S Simulation -B build-simulation
cmake --build build-simulation --parallel 4
```

common counting needs neither ROOT nor Geant4. Merger needs ROOT only. Simulation needs all physics dependencies. Independent executables are in the respective build-*/bin; automated workflows intentionally use only unified build/bin.

Useful CMake arguments: ROOT_DIR, Geant4_DIR, HEALPIX_INCLUDE_DIR, HEALPIX_LIBRARY, optional CXXSUPPORT_LIBRARY, EFF_GEANT4_CONFIG, CMAKE_PREFIX_PATH. Pass actual paths through environment.sh or make configure CMAKE_ARGS="...". Use an escaped semicolon inside a CMAKE_PREFIX_PATH list, or use colon-separated environment CMAKE_PREFIX_PATH.

Source requiresC++17; CMake raises the standard if installed dependencies requireC++20. For a new compiler/dependency stack use a fresh build directory. The thin Makefile delegates library selection to CMake; do not scatter manual -I/-L/-l edits across modules.

cmake --build build --target clean removes build products, not runs.

## Validation boundary

Local count/workflow tests passed, but ROOT and Geant4 are unavailable on the delivery machine. ROOT roundtrip tests and actual MT transport must still run on the small server. See VALIDATION.md.
