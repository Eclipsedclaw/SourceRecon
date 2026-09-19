# Reconstruction — User Manual

## Build

On a new machine, configure dependencies once from the V7 root:

```bash
make configure
```

```bash
cd Reconstruction
make
```

This automatically builds `../common/libeiid_common.a` if needed. The executable is `EIID_Recon_V7`.

## Run

```bash
./EIID_Recon_V7 config/recon_config.json
```

## Editable parameters

File: `config/recon_config.json`.

| Parameter | Meaning |
|---|---|
| `input_events_file` | Compact event ROOT file |
| `input_events_tree` | Tree containing compact events |
| `output_result_file` | Output image ROOT file |
| `output_result_tree` | Tree written into the image file |
| `absolute_efficiency_file` | Resampled absolute-efficiency ROOT file |
| `absolute_efficiency_tree` | Tree containing `cell_index` and `efficiency` |
| `healpix_nside` | Reconstruction HEALPix Nside |
| `healpix_ordering` | Must be `RING` |
| `energy_min_MeV` | Lowest candidate incident energy |
| `energy_max_MeV` | Highest candidate incident energy |
| `energy_point_count` | Number of candidate energies |
| `iteration_count` | LM-MLEM iteration count |
| `response_sigma_degree` | Angular Gaussian width |
| `denominator_floor` | Numerical zero threshold |
| `event_branches.r1_x` | Branch holding the ch2 interaction x coordinate |
| `event_branches.r1_y` | Branch holding the ch2 interaction y coordinate |
| `event_branches.r1_z` | Branch holding the ch2 interaction z coordinate |
| `event_branches.r2_x` | Branch holding the ch1 interaction x coordinate |
| `event_branches.r2_y` | Branch holding the ch1 interaction y coordinate |
| `event_branches.r2_z` | Branch holding the ch1 interaction z coordinate |
| `event_branches.e1_MeV` | Branch holding the ch2 deposited energy |
| `result_branches.cell_index` | Flattened direction-energy cell index |
| `result_branches.weight` | Reconstructed cell intensity |
| `result_branches.healpix_pixel_id` | HEALPix direction pixel ID |
| `result_branches.theta_degree` | Direction polar angle in degrees |
| `result_branches.phi_degree` | Direction azimuth in degrees |
| `result_branches.direction_x` | Unit direction x component |
| `result_branches.direction_y` | Unit direction y component |
| `result_branches.direction_z` | Unit direction z component |
| `result_branches.energy_MeV` | Candidate energy at this cell |
| `absolute_efficiency_branches.cell_index` | Cell-index Branch in the efficiency file |
| `absolute_efficiency_branches.efficiency` | Absolute-efficiency Branch, normally named `efficiency` |

Relative paths are based on the JSON directory. The grid must exactly match the efficiency metadata. A mismatch is an error rather than an automatic resample; use GridResampler first.

Expected output is the configured `result.root`, which is directly readable by Visualization.
