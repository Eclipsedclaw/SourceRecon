# ResponseCalibration——用户手册

## 目录和运行

```text
config/  标定输入、分箱和输出
output/  JSON 数值结果
figures/ 拟合叠图
```

```bash
cd ResponseCalibration
make
./response_calibrator config/calibration_config.json
```

或在根目录执行 `make calibrate`。

参数：`inputs[].file/tree/level/compton_model`、输出 ROOT/参数 Tree/经验 PDF/JSON/图片目录、`scatter_angle_edges_degree`、ARM 格数与范围、每分箱最低训练/测试事件数和 `test_fraction`。`level=truth` 用于研究本征多普勒，`level=detector` 用于实际重建响应；程序拒绝混用两种 level 或错误的物理模型。

默认 `scatter_angle_edges_degree=[0,180]` 表示先对每个能量拟合一个全局 ARM 响应，暂不声称已测得散射角依赖。当前 ch2→ch1 几何主要接受前向散射，不能将 `[90,180]` 作为必填的独立分箱。只有当程序打印的实际角度覆盖和每分箱统计都充足时，才应继续细分。

如果任一能量—角度分箱统计不足，程序会停止并指出具体分箱。不要为了通过程序而降低门槛或伪造空分箱；应合并无法独立标定的区间，或生成更多样本。正式结果需检查 `voigt_converged`、`double_gaussian_converged` 和全部拟合图。
