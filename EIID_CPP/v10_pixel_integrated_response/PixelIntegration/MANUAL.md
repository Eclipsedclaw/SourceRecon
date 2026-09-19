# PixelIntegration — user manual

This library is normally built by Reconstruction. It can be built and tested independently:

```bash
make configure
make -C PixelIntegration
make -C PixelIntegration test
```

It produces `PixelIntegration/libpixel_integration.a`. Runtime control lives in a reconstruction JSON:

- `pixel_integration.strategy`: `pixel_center` or `healpix_subpixel`;
- `pixel_integration.integration_nside`: sampling-grid Nside.

Both Nsides and their ratio must be powers of two, and integration Nside cannot be smaller than the reconstructed parent Nside. Clean with `make -C PixelIntegration clean`.
