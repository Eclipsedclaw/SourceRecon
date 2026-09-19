# ResponseKernel — developer guide

```text
include/  IResponseKernel, query, table, implementations, reader, factory
src/      kernels, interpolation table, factory
io/       ROOT calibration reader
tests/    interpolation and normalization
```

The solver-independent interface returns a normalized ARM density in inverse degrees. The rectangular energy/angle parameter table is contiguous and bilinearly interpolated. ROOT ownership is confined to loading. Add models through the interface and factory, not by branching inside LM-MLEM.
