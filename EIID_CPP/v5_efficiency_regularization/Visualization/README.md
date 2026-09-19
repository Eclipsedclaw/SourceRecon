# Visualization — Developer README

Visualization is an independent ROOT plotting executable. It reads only the reconstruction result format and has no dependency on the simulation or LM-MLEM implementation.

## Files

- `iplotter.h`: polymorphic plot interface.
- `vis_config.h/.cpp`: plot and truth JSON parsing.
- `reconstruction_data.h/.cpp`: one-time `result.root` reader.
- `skymap_plotter.h/.cpp`: full-sky heat map; camera front (`-Z`) is at the display center.
- `spectrum_plotter.h/.cpp`: intensity marginalized over direction.
- `containment_plotter.h/.cpp`: angular cumulative distribution and R50/R68/R90.
- `plot_utils.h/.cpp`: shared transformations and grouping helpers.
- `vis_main.cpp`: constructs enabled plotters through `IPlotter` pointers.

To add a plot, implement `IPlotter`, add its source to `src/`, and register it in `vis_main.cpp`. The wildcard Makefile automatically compiles the new `.cpp` file.

The standalone Makefile reads ROOT, JSON, and rpath settings from `../config/local.mk`, generated once by the root `make configure` target.
