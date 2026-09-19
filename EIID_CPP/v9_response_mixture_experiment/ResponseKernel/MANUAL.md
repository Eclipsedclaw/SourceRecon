# ResponseKernel — user manual

```text
ResponseKernel/{include,src,io,tests} -> libresponse_kernel.a
```

This is a static library, not a command-line program.

```bash
cd ResponseKernel
make
make test
```

Select `fixed_gaussian`, `voigt`, `double_gaussian`, `gaussian_lorentzian_mixture`, or `histogram` through Reconstruction's `response_kernel` JSON object. The calibrated models require `doppler_response.root`.
