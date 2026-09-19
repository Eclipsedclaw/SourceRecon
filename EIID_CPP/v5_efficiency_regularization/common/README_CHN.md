# common——开发者说明

`common` 是重建模块和网格兼容器共同使用的轻量级静态库，不负责 ROOT 或 Geant4 对象的生命周期。

## 文件职责

- `include/Common.h`：定义项目统一浮点类型 `Decimal`、圆周率和电子静止质量。
- `include/PhysicsTypes.h`：定义 `Vec3`、紧凑事件 `Event` 和方向—能量单元 `Cell`。
- `include/IGrid.h`：只读网格抽象接口。
- `include/HealpixGrid.h`：采用 RING 排序的 HEALPix 网格实现。
- `src/HealpixGrid.cpp`：生成方向、能量和展平单元，并执行边界检查。
- `include/AbsoluteEfficiencyMap.h`：方向 × 能量绝对效率容器。
- `src/AbsoluteEfficiencyMap.cpp`：实现 O(1) 索引、重复赋值检查和完整性检查。
- `include/EfficiencyFileSchema.h`：统一 ROOT Branch 和元数据名称。
- `Makefile`：生成 `libeiid_common.a`。

## 固定索引顺序

展平索引规定为：

```text
cell_index = direction_index * energy_count + energy_index
```

这条规则属于磁盘数据格式的一部分。若修改它，旧 ROOT 文件也必须进行格式迁移。

## 扩展接口

如需支持另一种球面网格，应实现 `IGrid`。除非某项算法必须使用 HEALPix 几何，否则求解器和插值策略不应直接依赖 `HealpixGrid`。

`AbsoluteEfficiencyMap` 只接受 `[0,1]` 范围内的有限数值，并且每个单元只能赋值一次。

## 编译配置

Makefile 读取根目录 `configure.sh` 一次生成的 `../config/local.mk`，不会再根据空的 `CONDA_PREFIX` 猜测错误路径。无需配置依赖也可以先运行轻量测试 `make test`。
