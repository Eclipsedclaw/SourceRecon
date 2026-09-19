# EIID V7 User Manual

## 1. What this project does

V7 provides five user-facing programs:

| Program | Purpose |
|---|---|
| `Geant4_Simulation/geant4_simulator` | Generate an absolute-efficiency map or compact events |
| `GridResampler/grid_resampler` | Convert a Master efficiency grid to the reconstruction grid |
| `Translator/eiid_translator` | Convert raw Geant4 Step data to compact events |
| `Reconstruction/EIID_Recon_V7` | Run EIID + LM-MLEM reconstruction |
| `Visualization/eiid_plotter` | Generate base plots, fit diagnostics, and a JSON summary |

The usual workflow is:

```text
Mode 0 simulation → Master absolute efficiency → resampling → efficiency
Mode 1 simulation or Translator → events
efficiency + events → reconstruction → result.root → visualization
```

## 2. Required environment

The build expects:

- C++20-capable compiler (`g++`)
- GNU Make
- CERN ROOT with `root-config`
- HEALPix C++ (`healpix_cxx` and `cxxsupport`)
- `nlohmann/json.hpp`
- Geant4 with `geant4-config` for the simulation module

The project does not require a permanently activated Conda shell. Configure the machine once from the V7 root:

```bash
make configure
```

This generates `config/local.mk` with absolute dependency paths. Useful checks after configuration are:

```bash
root-config --version
pkg-config --libs healpix_cxx
geant4-config --version
cat config/local.mk
```

Geant4 discovery compares candidates from `PATH`, common environments, HOME, `/opt`, and `/usr/local`; it excludes `*-build` directories and chooses the highest installed version. Use `make show-config` to see the exact compiler and Geant4 selected.

## 3. Compilation

From the V7 root:

```bash
make configure      # required once per machine
make v7-all
```

Subsequent terminals only need `make v7-all`; environment activation is unnecessary. After moving to another server, delete or overwrite `config/local.mk` by running `make configure` again.

Build one module only:

```bash
make common
make reconstruction
make resampler
make simulation
make translator
make visualization
```

Or enter a module directly:

```bash
cd Reconstruction
make
```

Clean all modules:

```bash
make clean
```

## 4. Geant4 simulation configuration

File: `Geant4_Simulation/config/sim_config.json`.

### Top level

| Parameter | Meaning |
|---|---|
| `mode` | `0`: absolute-efficiency table; `1`: compact triggered events |
| `random_seed` | Positive CLHEP random seed |

### `source`

| Parameter | Meaning |
|---|---|
| `particle_name` | Geant4 particle name, normally `gamma` |
| `hemisphere_radius_mm` | Point-source distance from the ch2 geometrical center |
| `front_hemisphere_only` | `true`: only HEALPix directions with `z <= 0`; `false`: full sphere |
| `emission_cone_safety_margin_degree` | Added to the geometry-derived cone half-angle; it is not the cone angle itself |

The source position for cell `j` is `ch2Center + radius * direction[j]`. Increasing radius makes incident rays more nearly parallel but reduces absolute efficiency approximately as `1/R²`.

### `environment`

| Parameter | Meaning |
|---|---|
| `world_material` | `G4_Galactic` for vacuum or `G4_AIR` for laboratory air |
| `world_margin_mm` | Extra World boundary outside all source positions and detector parts |

The World size is automatic. Do not manually edit the World dimensions when changing the source radius.

### `grid`

| Parameter | Meaning |
|---|---|
| `healpix_nside` | HEALPix resolution; positive power of two |
| `energy_point_count` | Number of simulated incident-energy points |
| `energy_min_MeV` | Minimum incident energy |
| `energy_max_MeV` | Maximum incident energy |
| `particles_per_cell` | Cone-sampled photons for every active direction–energy cell |

Full direction count is `12 × Nside²`. Runtime grows linearly with active directions, energy points, and particles per cell.

### `trigger`

| Parameter | Meaning |
|---|---|
| `front_chamber_id` | Must be `0` for ch2 in this detector geometry |
| `rear_chamber_id` | Must be `1` for ch1 |
| `minimum_layer_energy_MeV` | Minimum deposited energy required independently in ch2 and ch1 |

### `output`

| Parameter | Meaning |
|---|---|
| `absolute_efficiency_root_file` | Mode 0 output path |
| `absolute_efficiency_tree_name` | Mode 0 Tree name |
| `events_root_file` | Mode 1 output path |
| `events_tree_name` | Mode 1 Tree name |

All relative paths are resolved against `sim_config.json`.

Run independently:

```bash
cd Geant4_Simulation
make run
```

`make run` evaluates the `geant4-config --sh` command selected in
`config/local.mk` before launching the executable. This loads the matching
Geant4 libraries and datasets even in a fresh terminal. To select another
configuration file, use `make run SIM_CONFIG=config/quick_test.json`.

## 5. Grid resampler configuration

File: `GridResampler/config/resampler_config.json`.

| Parameter | Meaning |
|---|---|
| `input_absolute_efficiency_file` | Master efficiency ROOT file |
| `input_absolute_efficiency_tree` | Master Tree name |
| `output_absolute_efficiency_file` | Resampled output ROOT file |
| `output_absolute_efficiency_tree` | Output Tree name |
| `master_grid.healpix_nside` | Nside used by Mode 0 simulation |
| `master_grid.energy_min_MeV` | Master minimum energy |
| `master_grid.energy_max_MeV` | Master maximum energy |
| `master_grid.energy_point_count` | Master energy count |
| `target_grid.healpix_nside` | Reconstruction HEALPix Nside to produce |
| `target_grid.energy_min_MeV` | Target minimum energy |
| `target_grid.energy_max_MeV` | Target maximum energy |
| `target_grid.energy_point_count` | Target energy count |
| `interpolation` | `nearest` or `polygon` |
| `polygon_subdivision_factor` | Common-refinement multiplier for polygon mode; larger is more accurate and slower |
| `require_full_coverage` | Fail if a Target pixel receives no Master micro-pixel coverage |

The Target energy interval must lie inside the Master interval. The source radius metadata is preserved automatically.

Run:

```bash
cd GridResampler
./grid_resampler config/resampler_config.json
```

## 6. Reconstruction configuration

File: `Reconstruction/config/recon_config.json`.

### Files and grids

| Parameter | Meaning |
|---|---|
| `input_events_file` | Compact event ROOT file |
| `input_events_tree` | Compact event Tree name |
| `output_result_file` | Reconstructed image ROOT file |
| `output_result_tree` | Reconstructed image Tree name |
| `absolute_efficiency_file` | Efficiency map ROOT file |
| `absolute_efficiency_tree` | Efficiency Tree name |
| `healpix_nside` | Reconstruction direction-grid Nside |
| `healpix_ordering` | Must be `RING` |
| `energy_min_MeV` | Reconstruction minimum incident energy |
| `energy_max_MeV` | Reconstruction maximum incident energy |
| `energy_point_count` | Reconstruction energy-grid count |

The reconstruction grid must match the resampled efficiency metadata exactly.

### Algorithm parameters

| Parameter | Meaning |
|---|---|
| `iteration_count` | Number of LM-MLEM iterations |
| `response_sigma_degree` | Width of the angular Gaussian response kernel |
| `denominator_floor` | Numerical zero guard for vector lengths and predictions |

### Branch names

| Parameter | Meaning |
|---|---|
| `event_branches.r1_x` | ch2 interaction x Branch |
| `event_branches.r1_y` | ch2 interaction y Branch |
| `event_branches.r1_z` | ch2 interaction z Branch |
| `event_branches.r2_x` | ch1 interaction x Branch |
| `event_branches.r2_y` | ch1 interaction y Branch |
| `event_branches.r2_z` | ch1 interaction z Branch |
| `event_branches.e1_MeV` | ch2 deposited-energy Branch |
| `result_branches.cell_index` | Flattened output cell index |
| `result_branches.weight` | Reconstructed intensity |
| `result_branches.healpix_pixel_id` | HEALPix pixel ID |
| `result_branches.theta_degree` | Polar angle |
| `result_branches.phi_degree` | Azimuth |
| `result_branches.direction_x` | Direction x component |
| `result_branches.direction_y` | Direction y component |
| `result_branches.direction_z` | Direction z component |
| `result_branches.energy_MeV` | Cell energy |
| `absolute_efficiency_branches.cell_index` | Efficiency cell-index Branch |
| `absolute_efficiency_branches.efficiency` | Absolute-efficiency Branch, normally `efficiency` |

Run:

```bash
cd Reconstruction
./EIID_Recon_V7 config/recon_config.json
```

## 7. Translator configuration

File: `Translator/config/translator_config.json`.

| Parameter | Meaning |
|---|---|
| `raw_input_file` | Step-level Geant4 ROOT input |
| `raw_input_tree` | Step-level input Tree |
| `output_events_file` | Compact event ROOT output |
| `output_events_tree` | Compact output Tree |
| `front_chamber_id` | ch2 chamber ID, normally `0` |
| `rear_chamber_id` | ch1 chamber ID, normally `1` |
| `minimum_layer_energy_MeV` | Per-layer trigger threshold |
| `raw_branches.event_id` | Event grouping key |
| `raw_branches.chamber_id` | Detector layer ID |
| `raw_branches.x` | Step x-coordinate Branch |
| `raw_branches.y` | Step y-coordinate Branch |
| `raw_branches.z` | Step z-coordinate Branch |
| `raw_branches.energy_deposit_MeV` | Step energy-deposit name |
| `output_branches.r1_x` | ch2 centroid x output Branch |
| `output_branches.r1_y` | ch2 centroid y output Branch |
| `output_branches.r1_z` | ch2 centroid z output Branch |
| `output_branches.r2_x` | ch1 centroid x output Branch |
| `output_branches.r2_y` | ch1 centroid y output Branch |
| `output_branches.r2_z` | ch1 centroid z output Branch |
| `output_branches.e1_MeV` | ch2 total deposited-energy output Branch |

The raw input and output paths must differ. Input rows must be sorted by non-decreasing `eventID`.

Run:

```bash
cd Translator
./eiid_translator config/translator_config.json
```

## 8. Visualization configuration

Files: `Visualization/config/plot_config.json` and `truth_info.json`.

`plot_config.json`:

| Parameter | Meaning |
|---|---|
| `input_root_file` | Reconstruction result ROOT file |
| `input_tree_name` | Result Tree name |
| `output_directory` | PNG output directory |
| `truth_info_file` | Path to truth JSON |
| `draw_skymap` | Enable sky map |
| `draw_spectrum` | Enable energy spectrum |
| `draw_containment` | Enable containment plot |
| `draw_energy_metrics` | Enable direct-FWHM and shortest-interval energy plot |
| `draw_direction_metrics` | Enable tangent-plane centroid/covariance plot |
| `draw_energy_angle_map` | Enable energy–angular-distance map |
| `write_quality_summary` | Write `quality_summary.json` |
| `show_truth_markers` | Overlay truth direction/energy references |

`analysis` object:

| Parameter | Meaning |
|---|---|
| `energy_interval_fraction` | Fraction in the shortest contiguous energy interval |
| `gaussian_fit_enabled` | Enable optional Gaussian diagnostics |
| `gaussian_fit_half_width_MeV` | Optional energy-Gaussian half-window |
| `direction_local_radius_degree` | Local centroid/covariance radius |
| `direction_spectrum_radius_degree` | Circular direction gate for the final spectrum |

`truth_info.json`:

| Parameter | Meaning |
|---|---|
| `theta_degree` | True source HEALPix polar angle |
| `phi_degree` | True source azimuth |
| `energy_MeV` | True source energy |

Run:

```bash
cd Visualization
./eiid_plotter config/plot_config.json
```

The default directory is `Visualization/figures/`. V7 adds `energy_resolution.png`, `direction_resolution.png`, `energy_angle_map.png`, and `quality_summary.json`. Truth is used only for biases and markers, never peak selection. Gaussian failure is reported as unavailable; direct FWHM, shortest intervals, centroid/covariance, and R50/R68/R90 remain available.

## 9. Common workflows

### Build a reusable Master efficiency map

1. Set Geant4 `mode = 0`.
2. Choose the Master Nside/energy grid and a statistically meaningful `particles_per_cell`.
3. Run `geant4_simulator`.
4. Inspect that `absolute_efficiency_master.root` exists.

### Convert Master efficiency to a cheaper reconstruction grid

1. Copy the exact Master grid settings into `resampler_config.json`.
2. Set the desired Target grid.
3. Run `grid_resampler`.
4. Use its `absolute_efficiency.root` in reconstruction.

### Generate compact test data directly

1. Set Geant4 `mode = 1`.
2. Set source/grid parameters.
3. Run `geant4_simulator` to produce `events.root`.

Mode 1 is a cone-targeted triggered-event sample. The 4π absolute normalization is applied to Mode 0 efficiency, not as an event weight in Mode 1.

Compact `events.root` data are independent of the efficiency estimator. Older compact events remain valid in V7 when their Tree/Branches, units, and `r1=ch2, r2=ch1` convention match. The artifact that must be regenerated by V7 is the absolute-efficiency map.

### Translate an existing raw Geant4 file

1. Configure `Translator/config/translator_config.json`.
2. Run `eiid_translator`.
3. Point reconstruction at the resulting `events.root`.

### Full reconstruction and plots

```bash
./Reconstruction/EIID_Recon_V7 Reconstruction/config/recon_config.json
./Visualization/eiid_plotter Visualization/config/plot_config.json
# Equivalent shortcut: make run-visualization
```

## 10. Manually adjusting Makefiles

Prefer rerunning the configurator instead of editing every module Makefile:

```bash
EIID_DEPS_PREFIX=/path/to/dependency/prefix \
ROOT_CONFIG=/path/to/root-config \
GEANT4_CONFIG=/path/to/geant4-config \
make configure
```

The generated `config/local.mk` contains explicit entries such as:

```make
PROJECT_CXX_STANDARD := c++20
CXX := /absolute/path/to/g++
HEALPIX_CFLAGS := -I/absolute/prefix/include/healpix_cxx
HEALPIX_LIBS := -L/absolute/prefix/lib -lhealpix_cxx -lcxxsupport
EIID_RPATH_FLAGS := -Wl,-rpath,/absolute/prefix/lib
```

Do not copy `-std=` options from `root-config` or `geant4-config` into module Makefiles. They are deliberately filtered; `PROJECT_CXX_STANDARD` is appended last as the only project language-standard switch.

If automatic discovery cannot find JSON, ROOT, or Geant4, pass the corresponding absolute prefix/config executable to `make configure`. As a last resort, copy `config/local.mk.example` to `config/local.mk` and edit only that file. Do not edit six module Makefiles separately.

An independently invoked module may use another configuration file with `make EIID_LOCAL_CONFIG=/absolute/path/to/local.mk`.

For example, an external JSON include directory is represented by:

```make
JSON_CFLAGS := -I/path/containing/nlohmann
```

Do not add Geant4 libraries to unrelated modules. Do not combine all object files into one executable; module separation is intentional.

## 11. Important physics checks

- `hemisphere_radius_mm` is measured from ch2 center, not from the global origin.
- Changing the radius changes the absolute efficiency; regenerate the map.
- Increasing cone safety margin should leave the corrected absolute efficiency stable within Monte Carlo uncertainty. If it rises systematically, the previous cone was too narrow.
- Master and Target energy ranges, ordering, and Nside are validated at runtime.
- A small `particles_per_cell` is suitable only for smoke tests, not final calibration.
