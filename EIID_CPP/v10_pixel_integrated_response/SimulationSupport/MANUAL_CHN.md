# SimulationSupport——用户手册

## 定位与目录

这是内部支撑库，普通用户不需要单独运行。

```text
include/ -> 公共 schema
src/     -> 静态库实现
tests/   -> 最小契约测试
```

独立编译和测试：

```bash
cd SimulationSupport
make
make test
```

输出 `libsimulation_support.a`。本模块没有 JSON 参数；Branch 名属于磁盘格式，不能当作普通运行参数随意修改。
