# Visualization — User Manual

```text
Visualization/{config,include,src,figures} -> eiid_plotter
```

## Build and run

```bash
cd v8_doppler_response
make configure
make visualization
make run-visualization
```

Direct execution:

```bash
./Visualization/eiid_plotter Visualization/config/plot_config.json
```

ROOT runs in batch mode; X11 is not required.

## Configuration

Top-level switches are `draw_skymap`, `draw_spectrum`, `draw_containment`, `draw_energy_metrics`, `draw_direction_metrics`, `draw_energy_angle_map`, `write_quality_summary`, and `show_truth_markers`.

The `analysis` object contains:

- `energy_interval_fraction`: intensity fraction for the shortest contiguous energy interval.
- `gaussian_fit_enabled`: enable optional Gaussian diagnostics.
- `gaussian_fit_half_width_MeV`: optional energy-fit half-window.
- `direction_local_radius_degree`: local tangent-plane analysis radius.
- `direction_spectrum_radius_degree`: circular direction gate for the final spectrum.

Outputs are `energy_resolution.png`, `direction_resolution.png`, `energy_angle_map.png`, and `quality_summary.json`, plus the original sky map, spectrum, and containment plots when enabled.

Primary quantities are direct FWHM, shortest intensity interval, weighted direction centroid/covariance, and R50/R68/R90. Optional Gaussian failure does not invalidate them.
