# 0.662 MeV 原始效率图：cluster 高统计量切片

这是独立展示文件夹，不是新的重建版本。未修改历史版本、模拟结果或效率值。
ROOT 原始数据来自 cluster 的 `efficiency_map_batch/runs/slice_001/raw_efficiency_master.root`。

## 运行与文件

小服务器路径：`/home/ezqi/labwork/SourceRecon/EIID_CPP/efficiency_slice_0662_cluster_20260919`。

```bash
cd /home/ezqi/labwork/SourceRecon/EIID_CPP/efficiency_slice_0662_cluster_20260919
bash run.sh
```

`run.sh` 核对原始文件 SHA256，使用小服务器已安装的 ROOT，先核对逐格计数和效率公式，
再将图片、数字摘要、终端输出日志写入 `figures/`。重运行只更新本文件夹的图和日志。
不会重新跑模拟。当前只需 ROOT，不需要 Python、Geant4 或重新安装 HEALPix。

- `input/raw_efficiency_master.root`：输入只读原始数据。
- `run_efficiency_slice.C`：检查实际能量、网格、发射数和效率公式；输出摘要后画图。
- `plot_raw_efficiency_map.C`：从既有已修复的 Quicklook 复制，使用 ROOT 画矩形图和 Hammer-Aitoff skymap。
- `figures/raw_efficiency_map_E0p662_linear.png`：线性色标矩形图。
- `figures/raw_efficiency_map_E0p662_log.png`：对数色标矩形图。
- `figures/raw_efficiency_map_E0p662_skymap_aitoff_log.png`：对数色标全天球投影。
- 同名 `.pdf`：用于报告/放大查看。
- `figures/summary.txt`：输入参数、统计量、效率范围。
- `figures/plot.log`：此次 ROOT 绘图完整终端日志。

## 如何看图

- 输入恰好就是 **0.662 MeV 单层**，没有做能量插值。
- Nside=16，全天球3072格；实际模拟前半球（含赤道中心格）1568格。
- 每个模拟格发射100万次，总计15.68亿次；有效双层触发164535次，1568格全部非零。
- 相机正前方 `-Z` 位于图中央 `(0°,0°)`。
- 矩形图横轴是相机坐标经度，纵轴是相机坐标纬度；正经度朝 `+X`，正纬度朝 `+Y`。
- 经纬度定义：`longitude=atan2(x,-z)`，`latitude=asin(y)`（单位方向向量）。
- skymap 是相同数据的 Hammer-Aitoff 等面积投影。底部和左侧的直角轴是**投影坐标**，
  不是任意位置都能直接读取的原始经纬度；不要将投影边缘畸变理解为物理形变。
- Viridis 色标：**深紫色效率低，黄色效率高**；不能用“颜色更深”判断效率更高。
- 右侧色标是无量纲的绝对探测概率，不是重建强度，也不是事件总数。
- 两张对数图使用同一效率上下限和调色板；线性图使用0到最大值，不能逐色直接对比线性/对数图。
- 灰色是没有模拟的后半球，不是物理效率零。对数图中的真实零值不会被加上小正数。
- 效率按输入 `k/N * cone_fraction` 展示；没有 Jeffreys 平滑、空间平滑或人为基线。
- 绘图光栅只是显示用细格，每个显示点取所属 HEALPix 格的值，不增加物理分辨率。

## 数据身份

cluster campaign_id：`37862e45aec5457e8c1f3a56ba23b1d3`。
cluster DAG：39915848.0；最终合并已校验。

SHA256：`0f248e0141e753ac091514e3c633046cb20d564cca944e91854b5781793ae069`。
