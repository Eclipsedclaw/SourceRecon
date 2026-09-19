# Visualization — User Manual

## Build and run

Run `make configure` once from the V5 root on a new machine. Afterwards:

```bash
cd Visualization
make
./eiid_plotter config/plot_config.json
```

## `plot_config.json`

| Parameter | Meaning |
|---|---|
| `input_root_file` | Reconstruction `result.root` path |
| `input_tree_name` | Normally `EiidImage` |
| `output_directory` | PNG destination |
| `truth_info_file` | Truth JSON path |
| `draw_skymap` | Enable/disable sky map |
| `draw_spectrum` | Enable/disable spectrum |
| `draw_containment` | Enable/disable containment plot |
| `show_truth_markers` | Enable truth marker/energy line |

## `truth_info.json`

| Parameter | Meaning |
|---|---|
| `theta_degree` | True polar angle in degrees |
| `phi_degree` | True azimuth in degrees |
| `energy_MeV` | True source energy |

The default output directory is `Visualization/figures/`. ROOT runs in batch mode, so X11 is not required.

Containment radii cannot be interpreted below the HEALPix pixel scale. The plot includes grid-resolution information to prevent a coarse-grid `R50 = 0°` from being mistaken for infinite angular resolution.
