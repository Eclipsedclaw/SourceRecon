# ResponseKernel——用户手册

## 定位与目录

这是由重建程序加载的响应模型静态库，没有单独运行入口。

```text
include/  公共接口
src/      模型与插值
io/       ROOT 标定文件读取
tests/    数值测试
```

```bash
cd ResponseKernel
make
make test
```

输出 `libresponse_kernel.a`。用户通过重建 JSON 的 `response_kernel.type` 选择 `fixed_gaussian`、`voigt`、`double_gaussian` 或 `histogram`，并指定标定文件、参数 Tree 或经验 PDF 名。
