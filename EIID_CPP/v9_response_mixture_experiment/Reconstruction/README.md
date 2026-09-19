# Reconstruction — Developer README

```text
Reconstruction/
├── config/   fixed-Gaussian, Voigt, double-Gaussian, and Gaussian-Lorentzian JSON
├── include/  configuration, IO, and solver interfaces
├── src/      EIID response, LM-MLEM, configuration, main
├── io/       ROOT event/efficiency readers and image writer
├── tests/    efficiency-weighted MLEM test
├── Makefile
├── README.md / README_CHN.md
└── MANUAL.md / MANUAL_CHN.md
```

This module composes compact ROOT events, a HEALPix grid, an absolute-efficiency map, a pluggable response kernel, and LM-MLEM. It builds independently as `EIID_Recon_V9`.

## Files and responsibilities

- `include/ReconConfig.h`, `src/ReconConfig.cpp`: parse/validate JSON and resolve paths relative to the config file.
- `include/IReconstructionSolver.h`: solver plug-in interface.
- `include/LmMlemSolver.h`, `src/LmMlemSolver.cpp`: list-mode multiplicative update with explicit `s_j > 0` protection.
- `include/EiidResponse.h`, `src/EiidResponse.cpp`: ARM query construction and injected `IResponseKernel` evaluation.
- `include/RootEventReader.h`, `io/RootEventReader.cpp`: compact-event input only.
- `include/RootEfficiencyReader.h`, `io/RootEfficiencyReader.cpp`: minimal efficiency Tree plus strict metadata validation.
- `include/RootImageWriter.h`, `io/RootImageWriter.cpp`: self-describing reconstruction output.
- `src/main.cpp`: composition root; no physics formula is hidden in the entry point.
- `config/recon_*.json`: fixed-Gaussian, Voigt, double-Gaussian, and Gaussian-Lorentzian-mixture runtime examples.
- `Makefile`: standalone build.

## Solver contract

`LmMlemSolver` depends on `IGrid`, `AbsoluteEfficiencyMap`, and `ReconConfig`. It does not open ROOT files. A new solver can implement `IReconstructionSolver` and be selected in `main.cpp` without modifying I/O classes.

`EiidResponse` constructs the ARM query and delegates `q_ij` to the injected kernel. V9 constructs the complete response and forward prediction as

\[
a_{ij}=\varepsilon_j q_{ij},
\qquad
\mu_i=\sum_j a_{ij}\lambda_j.
\]

Absolute efficiency therefore participates in the event prediction instead of appearing only as a final normalization divisor. True out-of-domain cells with `ε_j <= 0` start at zero and remain masked.

## Input guarantees

`RootEfficiencyReader` rejects files with mismatched Nside, ordering, direction count, energy count/range, missing source radius, or an efficiency definition other than the current 4π isotropic point-source absolute detection efficiency with Jeffreys regularization. `cell_index` duplicates, omissions, invalid values, and out-of-range indices are rejected by `AbsoluteEfficiencyMap`.

The standalone Makefile reads machine-local ROOT, HEALPix, JSON, and rpath settings from `../config/local.mk`; generate it once with the root `make configure` target.

`--validate-events-only <config>` validates the external ROOT file, tree, branches, and event count without loading efficiency or response calibration. The complete workflow runs this preflight before expensive simulations.
