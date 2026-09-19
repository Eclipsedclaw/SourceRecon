# ResponseKernel——用户手册

该模块是重建程序加载的静态库，没有独立的数据处理入口。

```bash
cd ResponseKernel
make
make test
```

输出 `libresponse_kernel.a`。在 Reconstruction JSON 的 `response_kernel.type` 中选择：

- `fixed_gaussian`
- `voigt`
- `double_gaussian`
- `gaussian_lorentzian_mixture`
- `histogram`

除固定高斯外，模型通常需要 `calibration_file` 和 `parameter_tree`；经验直方图还需要 `histogram_name`。V10 的像素积分对照固定使用已通过标定门禁的 `gaussian_lorentzian_mixture`，避免在比较网格时同时改变响应模型。
