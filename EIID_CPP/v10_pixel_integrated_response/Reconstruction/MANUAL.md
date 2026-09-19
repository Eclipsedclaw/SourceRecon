# Reconstruction — user manual

```bash
make configure
make reconstruction
./Reconstruction/EIID_Recon_V10 Reconstruction/config/recon_config.json
```

Validate the external event file only with `EIID_Recon_V10 --validate-events-only <config>`.

Configuration covers event/result/efficiency ROOT paths and trees, parent HEALPix Nside, energy range/count, iterations, response-kernel calibration, numerical floor and branch mappings. V10 adds:

```json
"pixel_integration": {
    "strategy": "healpix_subpixel",
    "integration_nside": 64
}
```

Use root targets `reconstruct-center`, `reconstruct-integrated-16`, `reconstruct-integrated-32`, and `reconstruct-iteration-20`. Outputs are written under `runs/latest/reconstruction/`. The default is parent Nside 32, integration Nside 64 and 10 iterations.
