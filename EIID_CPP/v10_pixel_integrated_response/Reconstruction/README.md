# Reconstruction — developer guide

```text
Reconstruction/
├── config/                          V10 controlled configurations
├── include/ReconConfig.h
├── include/IReconstructionSolver.h
├── include/ISystemResponseEvaluator.h
├── include/PointSystemResponseEvaluator.h
├── include/PixelIntegratedResponseEvaluator.h
├── include/SystemResponseFactory.h
├── include/LmMlemSolver.h and EiidResponse.h
├── include/Root*.h
├── src/ and io/
├── tests/
└── Makefile -> EIID_Recon_V10
```

`EiidResponse` evaluates one candidate direction. A system-response evaluator either uses the parent centre or averages those evaluations over injected subpixel directions. `LmMlemSolver` depends only on the evaluator interface.

The complete response is `a_ij = efficiency_j * qbar_ij`; the same efficiency participates in the forward prediction and final sensitivity normalization. Non-positive-efficiency cells remain outside the reconstructed domain.

Missing `pixel_integration` configuration selects the historical centre strategy. Invalid power-of-two hierarchy and numerical settings fail before reconstruction allocation.
