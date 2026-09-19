# DopplerSampleGenerator——用户手册

## 目录和命令

```text
config/  可调 JSON
include/ + src/  Geant4 实现
io/      ROOT 输出
output/  free/Livermore 单点诊断输出
```

```bash
cd DopplerSampleGenerator
make
make run-free
make run-livermore
make run-calibration-grid
```

`run-calibration-grid` 顺序运行 0.3、0.5、0.662、1.0、2.0 MeV 五个 Livermore 配置。这五份正式标定样本写入 `runs/latest/calibration/samples/`；不会生成或覆盖项目根目录的外部 `events.root`。

可调参数：`experiment_name`、`random_seed`、`number_of_events`；`physics` 中的模型和原子退激发；`source` 中的粒子、能量、方向、到 ch2 中心的距离和发射锥安全余量；`environment` 的材料/World 余量；`selection` 的层编号和能量阈值；`output` 的 ROOT、Tree 和 JSON 路径。

单纯运行已经编译的程序：

```bash
./doppler_sample_generator config/livermore_0p662.json
```

在共享服务器上推荐 `make run-*`，因为它会在同一条命令内载入与编译版本匹配的 Geant4 数据集。
