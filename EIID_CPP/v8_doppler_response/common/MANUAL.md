# common — User Manual

```text
common/{include,src,tests} -> libeiid_common.a
```

This library is normally built automatically by Reconstruction or GridResampler. On a new machine, first run `make configure` from the V8 root.

Build it directly:

```bash
cd common
make
```

Output:

```text
libeiid_common.a
```

Clean:

```bash
make clean
```

There is no JSON configuration and no executable. To change project-wide floating-point precision, edit the single `Decimal` definition in `include/Common.h`, then clean and rebuild dependent modules.

HEALPix paths are stored in `../config/local.mk`. Inspect these generated locations if compilation reports a missing header or library:

```text
HEALPIX_CFLAGS := -I/absolute/path/include/healpix_cxx
HEALPIX_LIBS := -L/absolute/path/lib -lhealpix_cxx -lcxxsupport
```

Do not edit `common/Makefile` for a machine path; rerun the root configurator.
