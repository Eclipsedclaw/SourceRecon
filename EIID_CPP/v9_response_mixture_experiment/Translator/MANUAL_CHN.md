# Translator——用户手册

```text
Translator/{config,include,src} -> eiid_translator
```

## 编译与运行

新机器先在 V9 根目录执行一次 `make configure`，以后直接运行：

```bash
cd Translator
make
./eiid_translator config/translator_config.json
```

## 可调参数

| 参数 | 含义 |
|---|---|
| `raw_input_file` | Step 级原始 ROOT 文件路径 |
| `raw_input_tree` | 原始 Tree 名，通常为 `Tree1` |
| `output_events_file` | 精简事件 ROOT 输出路径 |
| `output_events_tree` | 精简 Tree 名，通常为 `Events` |
| `front_chamber_id` | ch2 编号 |
| `rear_chamber_id` | ch1 编号 |
| `minimum_layer_energy_MeV` | 两层各自必须达到的最低沉积能量 |
| `raw_branches.event_id` | 事件分组 Branch |
| `raw_branches.chamber_id` | 探测层编号 Branch |
| `raw_branches.x` | Step x 坐标 Branch |
| `raw_branches.y` | Step y 坐标 Branch |
| `raw_branches.z` | Step z 坐标 Branch |
| `raw_branches.energy_deposit_MeV` | Step 沉积能量 Branch |
| `output_branches.r1_x` | ch2 质心 x 输出 Branch |
| `output_branches.r1_y` | ch2 质心 y 输出 Branch |
| `output_branches.r1_z` | ch2 质心 z 输出 Branch |
| `output_branches.r2_x` | ch1 质心 x 输出 Branch |
| `output_branches.r2_y` | ch1 质心 y 输出 Branch |
| `output_branches.r2_z` | ch1 质心 z 输出 Branch |
| `output_branches.e1_MeV` | ch2 总沉积能量输出 Branch |

输入必须按 `eventID` 非递减排列。程序禁止把原始输入和精简输出配置为同一路径。

若 Geant4 Mode 1 已直接生成 `events.root`，无需运行 Translator。
