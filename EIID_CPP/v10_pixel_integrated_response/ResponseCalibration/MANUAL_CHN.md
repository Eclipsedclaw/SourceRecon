# ResponseCalibration——用户手册

## 运行

在 V10 根目录执行：

```bash
make calibrate
```

或单独运行：

```bash
cd ResponseCalibration
make
./response_calibrator config/calibration_config.json
```

默认结果位于：

```text
runs/latest/calibration/
├── doppler_response.root
├── model_comparison.json
├── model_status.json
└── figures/                    每个分箱的线性和对数纵轴拟合图
```

## 配置参数

- `inputs[]`：标定样本列表；`file`、`tree`、`level`、`compton_model` 必须与文件一致。
- `energy_edges_MeV`：入射能量分箱边界。
- `scatter_angle_edges_degree`：真实散射角分箱边界。
- `arm_bin_count`、`arm_min_degree`、`arm_max_degree`：ARM 直方图范围与格数。
- `minimum_training_events`、`minimum_test_events`：每个分箱允许拟合所需的最低统计。
- `test_fraction`：留作独立测试集的比例。
- `output_root_file`、`output_parameter_tree`、`output_histogram_name`：ROOT 输出位置和对象名。
- `output_comparison_json`：逐分箱指标文件。
- `output_model_status_json`：三模型总体可用性文件。
- `figures_directory`：拟合图目录。

## 必须检查的结果

正式重建前先看 `model_status.json`。`usable=false` 表示至少一个必需分箱未收敛；根目录的一键流程会跳过该模型，而不会拿失败参数继续重建。需要定位原因时查看 ROOT/JSON 中的 `fit_status`、`covariance_status`、`edm`、`function_calls` 和对应拟合图。

可直接查询模型门控：

```bash
./ResponseCalibration/response_calibrator \
  --model-usable runs/latest/calibration/model_status.json voigt
```

返回码 `0` 表示可用，`2` 表示科学性跳过，其他返回码表示文件或程序错误。
