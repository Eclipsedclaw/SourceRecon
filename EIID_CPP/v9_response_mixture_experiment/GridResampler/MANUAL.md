# GridResampler — User Manual

```text
GridResampler/{config,include,src} -> grid_resampler
```

## Build and run

Run `make configure` once from the V9 root on a new machine. Afterwards this module is independently buildable:

```bash
cd GridResampler
make
./grid_resampler config/resampler_config.json
```

## Configuration

| Parameter | Meaning |
|---|---|
| `input_absolute_efficiency_file` | Master absolute-efficiency ROOT file |
| `input_absolute_efficiency_tree` | Master Tree name |
| `output_absolute_efficiency_file` | Target absolute-efficiency ROOT file |
| `output_absolute_efficiency_tree` | Target Tree name |
| `master_grid.healpix_nside` | Nside used in Geant4 Mode 0 |
| `master_grid.energy_min_MeV` | Lowest Master-grid energy |
| `master_grid.energy_max_MeV` | Highest Master-grid energy |
| `master_grid.energy_point_count` | Master energy count |
| `target_grid.healpix_nside` | Nside required by Reconstruction |
| `target_grid.energy_min_MeV` | Lowest Target-grid energy |
| `target_grid.energy_max_MeV` | Highest Target-grid energy |
| `target_grid.energy_point_count` | Target energy count |
| `interpolation` | `nearest` or `polygon` |
| `polygon_subdivision_factor` | Accuracy/cost multiplier for polygon mode |
| `require_full_coverage` | Fail on any uncovered Target pixel |

Use `nearest` for quick checks. Use `polygon` for production grid conversion and increase the subdivision factor until the result is stable.

The Target energy range must be inside the Master range. The program preserves `source_radius_mm`; it must not combine maps produced at different source radii.
