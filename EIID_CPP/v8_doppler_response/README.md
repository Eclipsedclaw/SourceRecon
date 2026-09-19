# EIID V8 Doppler-response architecture — developer guide

## Orientation

This README describes architecture, interfaces, data contracts, and extension points. See `MANUAL.md` for configuration and commands. V8 is a copy-on-write successor of V7; the V7 directory is untouched.

## Tree

```text
v8_doppler_response/
├── common/                    physics types, HEALPix grid, efficiency map
├── SimulationSupport/         shared calibration-sample schema
├── Geant4_Simulation/         production efficiency/event simulator
├── GridResampler/             master-to-reconstruction efficiency converter
├── Translator/                raw-step ETL
├── DopplerSampleGenerator/    free/bound-electron calibration samples
├── ResponseCalibration/       Voigt and double-Gaussian fitting
├── ResponseKernel/            pluggable normalized response kernels
├── Reconstruction/           EIID and LM-MLEM composition root
├── KernelBenchmark/           end-to-end model comparison
├── Visualization/             model-independent V7 plots and metrics
├── legacy_v3_snapshot/        historical audit snapshot
├── config/                    machine-local dependency configuration
├── Makefile / configure.sh
├── README.md / README_CHN.md  developer documentation
└── MANUAL.md / MANUAL_CHN.md  user documentation
```

Every module has its own Makefile and four developer/user documents.

## Data flow

```text
Geant4 Mode 0 -> master efficiency -> GridResampler -> absolute_efficiency.root
Geant4 Mode 1 or Translator -----------------------> events.root
events + efficiency -> Reconstruction -> result.root -> Visualization

DopplerSampleGenerator -> Livermore samples -> ResponseCalibration
    -> doppler_response.root -> ResponseKernel -> Reconstruction
    -> result_voigt.root + result_double_gaussian.root -> KernelBenchmark
```

Efficiency is an absolute trigger probability. A response kernel is the conditional ARM probability density for an already specified event/candidate cell. They remain separate factors:

```text
q_ij = K(theta_geometry - theta_energy, E_j, theta_energy)
a_ij = efficiency_j * q_ij
```

## New boundaries

- `SimulationSupport::CalibrationSchema` is the single ROOT naming contract shared by sample production and calibration.
- `DopplerSampleGenerator` reuses the validated V7 Geant4 geometry and escape-Compton selection. Full absorption is not required.
- The response interface can condition on incident energy and scatter angle, but the default low-statistics calibration uses one `[0,180]` angle interval. The first generated table is therefore energy-dependent only and does not claim measured scatter-angle dependence. Default samples also share one source direction, so direction invariance requires separate multi-direction closure tests.
- `ResponseCalibration` bins samples in incident energy and reconstructed kinematic scatter angle (the same `theta_energy` coordinate queried during reconstruction), performs a deterministic train/test split, fits both models to identical training data, and writes training AIC/BIC plus held-out NLL.
- `IResponseKernel` is solver-independent. Implementations are fixed Gaussian, Voigt, double Gaussian, and empirical histogram.
- `KernelParameterTable` stores a rectangular 2-D table contiguously and performs bilinear interpolation with boundary clamping.
- `LmMlemSolver` receives one `IResponseKernel` by constructor injection; the solver is not duplicated by model.
- `KernelBenchmark` compares peak errors, energy moments, and R50/R68/R90 from two or more reconstructed images.

`doppler_response.root` contains `ResponseParameters` and `EmpiricalDetectorArmPdf`. Parameter rows must form a complete rectangular energy/angle grid. All kernels return normalized densities in inverse degrees.

When a parameterized kernel is selected, the ROOT reader also requires every row's model-specific convergence flag to be true. A failed fit therefore stops reconstruction instead of silently supplying invalid parameters.

## Extension rules

To add a parametric model, implement `IResponseKernel`, register it in `ResponseKernelFactory`, and optionally add an `IResponseFitter`. Do not modify `LmMlemSolver`. Add end-to-end metrics in `KernelBenchmark`; add ordinary physics plots through Visualization's `IPlotter` interface.

The V5 Jeffreys efficiency regularization, production simulator, resampler, translator, and model-independent V7 visualization are preserved.

Production use must also verify the response with calibration samples from multiple absolute sky directions; the default energy scan alone does not establish direction invariance.
