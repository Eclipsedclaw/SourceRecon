# PixelIntegration — developer guide

```text
PixelIntegration/
├── include/IPixelDirectionSampler.h
├── include/PixelCenterSampler.h
├── include/HealpixSubpixelSampler.h
├── include/SubpixelDirectionCache.h
├── src/
├── tests/test_pixel_sampling.cpp
├── Makefile
├── README.md / README_CHN.md
└── MANUAL.md / MANUAL_CHN.md
```

This library answers only where a parent pixel is sampled. It owns no events, response kernels, efficiencies or MLEM logic.

Public indices are RING ordered. The cache converts each parent to NESTED ordering, exploits the contiguous descendant range, converts child centres to `Vec3`, and exposes an allocation-free `std::span`. For parent and sampling Nsides `Np` and `Ns`, the number of equal-area samples is `(Ns/Np)^2`.

Add a new quadrature rule by implementing `IPixelDirectionSampler`; do not modify the solver.
