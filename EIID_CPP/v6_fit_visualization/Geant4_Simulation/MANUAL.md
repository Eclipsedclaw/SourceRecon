# Geant4_Simulation — User Manual

## Build

On a new machine, run `make configure` once from the V6 root. If Geant4 cannot be discovered automatically, use:

```bash
GEANT4_CONFIG=/absolute/path/to/geant4-config make configure
```

Automatic discovery compares PATH, HOME, `/opt`, and `/usr/local`, ignores `*-build` directories, and selects the highest installed Geant4 version. The module always uses the project-wide C++20 setting, even when an older `geant4-config` prints `-std=c++11`.

```bash
cd Geant4_Simulation
make
make run
```

No Conda activation is required after `config/local.mk` has been generated.
`make run` initializes the exact Geant4 runtime and datasets selected during
configuration. Use `make run SIM_CONFIG=config/another_config.json` for a
different simulation configuration.

## Run

```bash
make run
```

## Configuration parameters

| Group | Parameter | Meaning |
|---|---|---|
| top | `mode` | `0`: absolute efficiency; `1`: compact events |
| top | `random_seed` | Positive CLHEP seed |
| source | `particle_name` | Normally `gamma` |
| source | `hemisphere_radius_mm` | Distance from ch2 center to each point source |
| source | `front_hemisphere_only` | Restrict source directions to `z <= 0` |
| source | `emission_cone_safety_margin_degree` | Extra margin after automatic cone calculation |
| environment | `world_material` | `G4_Galactic` or `G4_AIR` |
| environment | `world_margin_mm` | Extra boundary outside source sphere/detector |
| grid | `healpix_nside` | Positive power-of-two Nside |
| grid | `energy_point_count` | Incident energy count |
| grid | `energy_min_MeV` | Lowest simulated incident energy |
| grid | `energy_max_MeV` | Highest simulated incident energy |
| grid | `particles_per_cell` | Simulated photons per active cell |
| trigger | `front_chamber_id` | Must be `0` (ch2) |
| trigger | `rear_chamber_id` | Must be `1` (ch1) |
| trigger | `minimum_layer_energy_MeV` | Required deposit in each layer |
| output | `absolute_efficiency_root_file` | Mode 0 output ROOT path |
| output | `absolute_efficiency_tree_name` | Mode 0 Tree name |
| output | `events_root_file` | Mode 1 output ROOT path |
| output | `events_tree_name` | Mode 1 Tree name |

## Mode 0

Use Mode 0 to create `absolute_efficiency_master.root`. Simulated zero-trigger cells use `(k+0.5)/(N+1)` smoothing, while cells outside the simulation domain remain exactly zero. Final production requires substantially more than the template's `100` particles per cell. Verify convergence by increasing the cone safety margin and particle count. As the count grows, the smoothed estimate automatically approaches ordinary `k/N`.

## Mode 1

Use Mode 1 to create compact triggered events directly. The output has `eventID`, `source_cell_index`, `r1`, `r2`, and `e1_MeV`.

Changing radius, World material, detector geometry, trigger threshold, or energy grid invalidates an existing absolute-efficiency calibration; rerun Mode 0.
