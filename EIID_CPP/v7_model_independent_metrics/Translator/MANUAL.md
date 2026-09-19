# Translator — User Manual

## Build and run

Run `make configure` once from the V7 root on a new machine. Afterwards:

```bash
cd Translator
make
./eiid_translator config/translator_config.json
```

## Configuration

| Parameter | Meaning |
|---|---|
| `raw_input_file` | Step-level input ROOT path |
| `raw_input_tree` | Raw Tree name, commonly `Tree1` |
| `output_events_file` | Compact output ROOT path |
| `output_events_tree` | Compact Tree name, normally `Events` |
| `front_chamber_id` | ch2 ID |
| `rear_chamber_id` | ch1 ID |
| `minimum_layer_energy_MeV` | Minimum deposit required in both layers |
| `raw_branches.event_id` | Event grouping Branch |
| `raw_branches.chamber_id` | Layer ID Branch |
| `raw_branches.x` | Step x coordinate Branch |
| `raw_branches.y` | Step y coordinate Branch |
| `raw_branches.z` | Step z coordinate Branch |
| `raw_branches.energy_deposit_MeV` | Step deposit energy |
| `output_branches.r1_x` | Output ch2 centroid x Branch |
| `output_branches.r1_y` | Output ch2 centroid y Branch |
| `output_branches.r1_z` | Output ch2 centroid z Branch |
| `output_branches.r2_x` | Output ch1 centroid x Branch |
| `output_branches.r2_y` | Output ch1 centroid y Branch |
| `output_branches.r2_z` | Output ch1 centroid z Branch |
| `output_branches.e1_MeV` | Output ch2 total deposited-energy Branch |

Input must be sorted by non-decreasing `eventID`. The program refuses to use the same path for raw input and compact output.

Skip this module when Geant4 Mode 1 already produced `events.root`.
