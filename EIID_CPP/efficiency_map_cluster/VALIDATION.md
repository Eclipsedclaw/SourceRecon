# Delivery validation record

## Dataset environment fallback, 2026-09-15

- User-provided server output confirms the previous probe fix passed configuration, simulator/merger build, C++ tests 2/2 and Python tests 15/15. Simulation then stopped at unset G4LEDATA despite all expected dataset directories being installed.
- Only cluster/setup_env.sh runtime logic changes in this patch; no C++, CMake, physics parameters or results are changed. It queries --datasets from the selected installation's sibling geant4-config.
- Six new environment-behavior tests and Bash syntax validation passed using temporary directories and metadata scripts.
- Full local Python suite: 18/21 passed; two unchanged CMake-dependent tests skipped without a persistent CMake installation, plus POSIX flock skipped on Windows. The earlier CMake checks were not rerun this round.
- The new wrapper still requires server execution. No real particle transport was run locally, and directory existence does not verify all dataset contents.

## test5 G4Run destructor repair, 2026-09-15

- The test5 stack locates the crash in G4Run::~G4Run. Official 11.2.2 source confirms it dereferences the current run manager; the old probe incorrectly constructed a G4Run without one.
- Replaced the orphan object with the out-of-line G4RunManager::GetRunManager() query. ROOT, HEALPix, library-path and normal-exit checks remain. Production physics, parameters and runtime wrappers are unchanged.
- Python: 14/15 passed, POSIX flock skipped on Windows (CMake3.31.6, GNU15.2). A new source-contract test forbids orphan G4Run construction and forced-exit workarounds; it is not a Geant4 execution test.
- The full physics stack is unavailable locally. The corrected combined probe and MT simulation still require server execution; local regression results do not establish end-to-end simulation success.

Previous validation rounds are retained below.

## Probe timeout diagnostics, 2026-09-15

- The new server log shows successful compile/link with Conda libstdc++, followed by a probe timeout. Its root cause is not established by the old buffered output.
- Added flushed stages, phase-specific failure reporting, and library checks before startup. This fixes diagnostics, not a confirmed cause of the server hang.
- Python: 13/14 passed, POSIX flock skipped on Windows. A compiled standard C++ executable tests success, exit 3, timeout with a marker and timeout without a marker. No fake physics headers are used.
- The full ROOT/Geant4/HEALPix probe and particle transport still cannot be run on this delivery machine.
- Unified pure-common configure/build passed again with GNU15.2/C++17/CMake3.31.6; CTest 1/1 passed.

## Build repair, 2026-09-13

- PUBLIC TreePlayer linkage and centralized discovery/runtime checks added; physics sources and production JSON unchanged.
- Rebuilt unified pure common and standalone common with GNU15.2/C++17; each CTest passed 1/1.
- Python: 12 tests, 11 passed, POSIX flock skipped on Windows. Five new tests cover linkage propagation, failed-config marker/log handling, stale-cache build/run refusal, runtime path handling and loaded-library path comparison.
- Real CMake missing-ROOT failure leaves no success marker. Both changed Bash scripts pass syntax checks. SHA256 comparison to the original ZIP confirms unchanged physical sources/config.
- **The delivery machine still lacks ROOT/Geant4/HEALPix. The new combined dependency probe and real MT transport have NOT run here.** The probe runs on the server during configure and blocks build on failure. Artificial ldd text and a simulated cmake exit status test orchestration only, not physics libraries.

The original delivery record is retained below.

Date: 2026-09-13. Source inspection is not presented as successful physics simulation.

## Executed

- Unified pure-common CMake build: GNU15.2, C++17, CMake3.31.6.
- Independent common build and CTest passed.
- CTest counts1/1 passed: manifest parsing, cross-cell boundaries, missing/invalid counters, zeros, integer merge, uint64 scale, invalid config and deterministic seed tests.
- Python suite:6 passed,1 POSIX flock test skipped on Windows. Coverage includes partitioning, large totals, frozen plans, EL7/EL9 submission templates, stdout/stderr capture, exit7 preservation, unique retry logs and CLI parsing.
- g++ -fsyntax-only passed for Merger orchestration/main and the ROOT-test caller. This excludes RootCountsIO.cpp and is not a ROOT link/runtime test.
- All three Bash entry scripts passed individual bash -n checks and use LF line endings.
- make -n smoke showed build-before-run ordering; it did not run transport.
- The ten inherited DetectorConstruction/DetectorMessenger/TrackerHit/TrackerSD/MyPhysicsList header/source files match the serial baseline SHA256.
- Official Geant4 11.2.2 CMake MT targets and thread-count API were inspected.
- No cluster jobs were submitted and no user ROOT data were generated or overwritten.

Tests use immutable fixtures, independent of editable production config.

## Not executed here

This Windows delivery environment lacks the ROOT/Geant4/HEALPix stack. Full Simulation compilation/linking, actual MT transport, actual ROOT I/O roundtrip, Linux/Lustre cross-node flock, real HTCondor submission/preemption and production performance remain to be tested on the target system.

make test includes a genuine ROOT roundtrip test for a configured ROOT machine. No stub interfaces were used to claim unavailable integration tests passed. Run the small-server smoke test before production.

## Corrections made during self-check

Explicit JSON copy initialization; consistent CMake minimum and standalone generated-header path; build-before-run smoke ordering; row/grid metadata verification of existing final files; readback-before-publish ROOT output; retained nonzero child exit status; unique attempt logs; legacy EL7 node selection fallback.

Temporary validation tools/build outputs are excluded from the source archive. The archive contains no machine-locked environment or physics results.
