# EIID V10 pixel-integrated response — developer guide

V10 is an isolated copy of V9; V9 remains untouched. Its single scientific change is to evaluate the conditional system response by equal-area quadrature inside each reconstructed HEALPix pixel instead of using only the pixel centre.

## Architecture

```text
v10_pixel_integrated_response/
├── common/                  shared types, HEALPix grid, efficiency container
├── PixelIntegration/        NEW direction samplers and subpixel cache
├── SimulationSupport/       calibration ROOT schema
├── Geant4_Simulation/       absolute-efficiency Master simulation
├── GridResampler/           Master -> Nside 8/16/32 efficiency maps
├── DopplerSampleGenerator/  response-calibration samples
├── ResponseCalibration/     response-model fitting and usability gate
├── ResponseKernel/          pluggable normalized ARM kernels
├── Reconstruction/         system-response factory, LM-MLEM and ROOT I/O
├── KernelBenchmark/         controlled pixel-integration comparison
├── Visualization/           independent plots and quality metrics
├── Translator/              optional Step ROOT -> compact-event ETL
├── scripts/                 run archival and configuration snapshot
├── config/local.mk          machine-local dependency discovery output
├── events.root              external read-only workflow input
├── Makefile
├── README*.md               developer documentation
└── MANUAL*.md               user documentation
```

```text
Geant4_Simulation -> Master efficiency -> GridResampler -----+
DopplerSampleGenerator -> ResponseCalibration -> Kernel -----+-> Reconstruction
external events.root ----------------------------------------+       |
                                                        Benchmark + Visualization
```

The optional Translator is not invoked by `make experiment`; its default output is `translated_events.root`, not the external `events.root`.

## Response integration

For parent pixel `j`, V10 evaluates

\[
\bar q_{ij}=\frac{1}{M}\sum_{k=1}^{M}
K(\theta_{geo}(i,\hat n_{jk})-\theta_{energy}(i,E_j)),
\qquad a_{ij}=\varepsilon_j\bar q_{ij}.
\]

All child centres have equal area. A 32 -> 64 refinement uses four samples per parent while retaining only the Nside-32 parent pixels as image unknowns.

```text
IPixelDirectionSampler
├── PixelCenterSampler
└── HealpixSubpixelSampler -> SubpixelDirectionCache

ISystemResponseEvaluator
├── PointSystemResponseEvaluator
└── PixelIntegratedResponseEvaluator
        ^
        +-- SystemResponseFactory
```

`LmMlemSolver` depends only on `ISystemResponseEvaluator`. Sampling rules and response evaluators can therefore be replaced independently of the solver.

## Invariants

- Public grids and ROOT files use RING order; hierarchical child lookup uses NESTED internally.
- `cell_index = direction_index * energy_count + energy_index`.
- Both Nsides and their refinement ratio must be powers of two.
- Samples per parent equal `(integration_nside / healpix_nside)^2`.
- Efficiency and conditional event-shape response remain separate factors.

## Controlled configurations

| Configuration | Parent | Integration | Samples | Iterations |
|---|---:|---:|---:|---:|
| centre control | 8 | 8 | 1 | 10 |
| integrated | 16 | 32 | 4 | 10 |
| preferred integrated | 32 | 64 | 4 | 10 |
| iteration control | 32 | 64 | 4 | 20 |

The leading runtime is approximately

\[
T\approx C N_{iter}N_{event}(12N_{side}^2)N_E M.
\]

Run `make test` for the child-mapping, centre-equivalence, efficiency-weighting and module contract tests. See [MANUAL.md](MANUAL.md) for operations.
