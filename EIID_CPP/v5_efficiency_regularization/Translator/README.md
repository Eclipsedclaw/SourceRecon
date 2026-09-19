# Translator — Developer README

Translator is an optional ETL executable for existing Step-level Geant4 ROOT files. It has no reconstruction or HEALPix dependency.

## Files

- `include/io_config.h`, `src/io_config.cpp`: path, Tree, Branch, trigger, and threshold configuration.
- `include/root_simulation_translator.h`: public translation entry.
- `src/root_simulation_translator.cpp`: streaming eventID state machine, digitizer, trigger policy, and compact ROOT writer.
- `src/translate_main.cpp`: independent composition root.
- `config/translator_config.json`: runtime schema mapping.

The input Tree is processed in one pass. Memory use scales with the number of Steps in one event, not the full file size. Same-chamber hits are collapsed to an energy-weighted centroid. Input and output files are checked to prevent accidental `RECREATE` overwrite of raw data.

The reconstruction-facing Event order is fixed: `r1/e1` belongs to ch2 and `r2` belongs to ch1.

The standalone Makefile reads ROOT, JSON, and rpath settings from `../config/local.mk`, generated once by the root `make configure` target.
