# common — Developer README

`common` is the dependency-light shared library used by reconstruction and grid resampling. It has no ROOT or Geant4 ownership.

## Files

- `include/Common.h`: project-wide `Decimal` precision and physical constants.
- `include/PhysicsTypes.h`: `Vec3`, `Event`, and direction–energy `Cell`.
- `include/IGrid.h`: abstract read-only grid contract.
- `include/HealpixGrid.h`: concrete RING-order HEALPix implementation.
- `src/HealpixGrid.cpp`: direction generation, energy generation, bounds checks, and flat cell ordering.
- `include/AbsoluteEfficiencyMap.h`: direction × energy efficiency container.
- `src/AbsoluteEfficiencyMap.cpp`: O(1) indexing, duplicate assignment checks, and completeness validation.
- `include/EfficiencyFileSchema.h`: canonical names shared by ROOT writers and readers.
- `Makefile`: builds `libeiid_common.a`.

## Stable ordering

The flat index is:

```text
cell_index = direction_index * energy_count + energy_index
```

This rule is part of the on-disk schema. Changing it requires a format migration.

## Extension points

To support another spherical grid, implement `IGrid`. Solvers and interpolation strategies must not depend on `HealpixGrid` directly unless they specifically require HEALPix geometry.

`AbsoluteEfficiencyMap` accepts only finite values in `[0,1]`. Each cell may be assigned exactly once.

## Build configuration

The Makefile reads `../config/local.mk`, generated once by the root `configure.sh`. It never infers a fallback from an empty `CONDA_PREFIX`. The dependency-light `make test` target remains available before configuration.
