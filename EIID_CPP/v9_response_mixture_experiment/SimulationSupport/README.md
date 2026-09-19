# SimulationSupport — developer guide

```text
SimulationSupport/
├── include/CalibrationSchema.h
├── src/CalibrationSchema.cpp
├── tests/test_calibration_schema.cpp
├── Makefile
├── README.md / README_CHN.md
└── MANUAL.md / MANUAL_CHN.md
```

This ROOT/Geant4-free static library is the single naming contract between calibration-sample writers and readers. It owns schema names, not selection or fitting logic.
