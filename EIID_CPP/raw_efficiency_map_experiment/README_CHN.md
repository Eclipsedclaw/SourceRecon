# 未平滑绝对效率实验

这是一个从 V10 独立复制出来的诊断实验，不会修改
`v10_pixel_integrated_response/`。它只回答一个问题：去掉 Jeffreys
`+0.5` 伪计数后，方向—能量效率图实际长什么样。

## 计算定义

主分支 `efficiency` 使用完全未平滑的频率估计：

```text
raw efficiency = valid_count / emitted_count
                 * cone_solid_angle_fraction
```

因此参与模拟但没有有效触发的 cell 保持严格零。ROOT 文件还保存：

- `valid_count`
- `emitted_count`
- `cone_solid_angle_fraction`
- `regularized_efficiency`（仅供与旧公式对照）

## 结构

```text
raw_efficiency_map_experiment/
├── common/include/          # 效率 ROOT schema
├── Geant4_Simulation/       # 独立的 Geant4 效率模拟器
├── Quicklook/               # 矩形图和逐像素 Hammer-Aitoff 图
├── runs/raw_efficiency/     # 新的 ROOT 输出
├── runs/smoke_test/         # 小规模验证专用输出
├── configure.sh
└── Makefile
```

Skymap 不再调用 ROOT 的 `Draw("AITOFF")` 填充等高线，而是对每个显示
像素做 Hammer-Aitoff 逆投影，再查询与矩形图相同的数据值。

## 2026-09-13 skymap 配色修复

`Quicklook/plot_raw_efficiency_map.C` 使用 `COL1 SAME0` 叠加投影像素，
避免普通 `SAME` 沿用空坐标框的 Z 范围。显示像素已经取对数，因此其
TPad 明确关闭 Logz；手画色标与矩形对数图使用相同的效率上下限，
包括“所有正效率相同”时的显示范围处理。原始计数、效率公式、方向投影
及 ROOT 输入均不变。已有结果只需运行 `make smoke-plot` 或 `make quicklook`。

## 2026-09-13 全零效率修复

- `PrimaryGeneratorAction`：用独立 `particleConfigured_` 标志记录初始化。
  首次生成前明确覆盖默认 geantino，并检查、打印粒子枪实际名称。
  Geant4 的默认粒子指针非空，旧的 nullptr 条件不能代表已设置 gamma。
- `TrackerSD`：运输步骤只有在没有沉积能量时才被忽略，保留边界步骤的
  实际能量沉积。两层触发阈值和未平滑效率公式保持原定义。
- `EventAction` / `RunAction`：增加 hit、前后层阈值、有效触发的运行摘要。
- `root_writer`：增加 `requested_event_count` 元数据用于检查完整计数。
- `Geant4_Simulation/tests/check_smoke_output.C`：只读核对真实模拟输出，
  检查重复/缺失 cell、完成事例数、有效计数和未平滑公式；全零触发不通过验收。
- `Quicklook`：支持全零图和单正值色标情况；小测试使用单独的输入及输出路径。
- `Makefile`：新增 `smoke`、`smoke-plot`；子模块补充 `.d` 头文件依赖及
  旧对象的重新编译依赖，避免类成员变更后使用旧布局。

本地已运行不依赖 Geant4/ROOT 的效率估计单元测试，检查了 Make 命令展开和
小测试配置。完整编译、实际 gamma 输运和 PNG 输出仍须在安装有依赖的
服务器运行 `make smoke` 与 `make smoke-plot` 验证。
