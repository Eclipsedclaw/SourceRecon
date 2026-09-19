# DopplerSampleGenerator — developer guide

```text
config/  model/energy/source/selection/output JSON
include/ interfaces, Geant4 actions, records, detector support
src/     implementations and composition root
io/      ROOT writer
output/  generated samples
```

This productionized successor of the V7 Doppler experiment creates truth- and detector-level escape-Compton response samples. It requires the first primary-gamma discrete interaction in ch2 and the next accepted interaction in ch1, but does not require full absorption. Production absolute efficiency remains the responsibility of `Geant4_Simulation`.
