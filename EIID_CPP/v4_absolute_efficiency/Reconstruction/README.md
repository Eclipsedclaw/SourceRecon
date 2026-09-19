# Reconstruction — Developer README

This module composes compact ROOT events, a HEALPix grid, an absolute-efficiency map, the EIID response kernel, and an LM-MLEM solver. It builds independently as `EIID_Recon_V4`.

## Files and responsibilities

- `include/ReconConfig.h`, `src/ReconConfig.cpp`: parse/validate JSON and resolve paths relative to the config file.
- `include/IReconstructionSolver.h`: solver plug-in interface.
- `include/LmMlemSolver.h`, `src/LmMlemSolver.cpp`: list-mode multiplicative update with explicit `s_j > 0` protection.
- `include/EiidResponse.h`, `src/EiidResponse.cpp`: Compton energy-angle and geometry-angle response.
- `include/RootEventReader.h`, `io/RootEventReader.cpp`: compact-event input only.
- `include/RootEfficiencyReader.h`, `io/RootEfficiencyReader.cpp`: minimal efficiency Tree plus strict metadata validation.
- `include/RootImageWriter.h`, `io/RootImageWriter.cpp`: self-describing reconstruction output.
- `src/main.cpp`: composition root; no physics formula is hidden in the entry point.
- `config/recon_config.json`: runtime parameters.
- `Makefile`: standalone build.

## Solver contract

`LmMlemSolver` depends on `IGrid`, `AbsoluteEfficiencyMap`, and `ReconConfig`. It does not open ROOT files. A new solver can implement `IReconstructionSolver` and be selected in `main.cpp` without modifying I/O classes.

For every cell, V4 applies the absolute efficiency in the LM-MLEM denominator. Non-positive-efficiency cells start at zero, remain zero, and are never divisors.

## Input guarantees

`RootEfficiencyReader` rejects files with mismatched Nside, ordering, direction count, energy count/range, missing source radius, or a non-V4 efficiency definition. `cell_index` duplicates, omissions, invalid values, and out-of-range indices are rejected by `AbsoluteEfficiencyMap`.

The standalone Makefile reads machine-local ROOT, HEALPix, JSON, and rpath settings from `../config/local.mk`; generate it once with the root `make configure` target.
