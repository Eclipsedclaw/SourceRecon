# common——用户手册

```text
common/{include,src,tests} -> libeiid_common.a
```

该库通常由 Reconstruction 或 GridResampler 自动编译。换到新机器后，先在 V8 根目录运行一次 `make configure`。

单独编译：

```bash
cd common
make
```

输出文件：

```text
libeiid_common.a
```

清理编译产物：

```bash
make clean
```

该模块没有 JSON 配置，也没有可执行程序。如需统一改变浮点计算精度，只需修改 `include/Common.h` 中的 `Decimal` 定义，然后执行 `make clean` 并重新编译依赖模块。

HEALPix 路径保存在 `../config/local.mk`。若编译提示找不到头文件或库，请检查其中自动生成的路径：

```text
HEALPIX_CFLAGS := -I/绝对路径/include/healpix_cxx
HEALPIX_LIBS := -L/绝对路径/lib -lhealpix_cxx -lcxxsupport
```

不要为了机器路径修改 `common/Makefile`，应重新运行根目录配置器。
