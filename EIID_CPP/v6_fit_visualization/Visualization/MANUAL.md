# Visualization — User Manual

## Build and run

```bash
cd v6_fit_visualization
make configure
make visualization
./Visualization/eiid_plotter Visualization/config/plot_config.json
# Or, from the root: make run-visualization
```

ROOT runs in batch mode; X11 is not required.

## `plot_config.json`

| Parameter | Meaning |
|---|---|
| `input_root_file` | Reconstruction `result.root` |
| `input_tree_name` | Normally `EiidImage` |
| `output_directory` | PNG and summary destination |
| `truth_info_file` | Independent truth JSON |
| `draw_skymap` | Write `skymap.png` |
| `draw_spectrum` | Write `spectrum.png` |
| `draw_containment` | Write `containment.png` |
| `draw_energy_fit` | Write `energy_fit.png` |
| `draw_direction_fit` | Write `direction_fit.png` |
| `draw_energy_angle_map` | Write `energy_angle_map.png` |
| `write_fit_summary` | Write `fit_summary.json` |
| `show_truth_markers` | Display truth references; never used for peak finding |

### `fit`

| Parameter | Meaning | Default |
|---|---|---|
| `energy_fit_half_width_MeV` | Energy fit half-window around the data peak | `0.16` |
| `direction_energy_gate_sigma` | Energy gate half-width in preliminary-fit sigma | `2.0` |
| `direction_fit_radius_degree` | Local direction-fit radius around the data peak | `30.0` |
| `direction_spectrum_radius_degree` | Direction gate for the final energy spectrum | `15.0` |

`truth_info.json` contains `theta_degree`, `phi_degree`, and `energy_MeV`. Truth affects markers, biases, and containment only.

V5 plot configurations remain valid: absent V6 switches default to disabled, and an absent `fit` object uses the defaults above.

Use `energy_fit.png` for energy bias/width/residuals, `direction_fit.png` for angular bias and elliptical widths, and `energy_angle_map.png` for direction–energy correlations. `fit_summary.json` supports batch comparisons.

MLEM weights are correlated. Gaussian widths are descriptive metrics, not formal statistical uncertainties; report them together with R50/R68/R90 and heed the HEALPix under-resolution warning.
