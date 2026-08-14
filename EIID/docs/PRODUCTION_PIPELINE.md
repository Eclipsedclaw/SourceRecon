# EIID 生产链交付说明

    离线 Geant4 primary/deposit/truth
      -> 独立数字化与 ch1+ch2 触发
      -> 完整节点统计 NPZ
      -> portable response library + SHA-256 + SUCCESS
      -> hybrid R(d|Omega,E) + selected s(Omega,E)
      -> sparse LM-MLEM
      -> numerical + 13 figures + telemetry + checkpoints
      -> memory-aware batch scheduler

当前 EIID 已实现从“节点统计 NPZ”开始的全部链路。原
`compton_satellite_sim` 的 legacy `Tree1` 缺少每个 primary（包括零 hit）的记录，
不能单独生成正式效率分母。程序会拒绝把这类统计伪装为正式响应；需要 Geant4
离线生产端按 `GEANT4_RESPONSE_DESIGN.md` 输出或汇总完整 primary 分母。

`geant4_formal_root` 输入适配器读取可配置的 `PrimaryTruth` 与
`DetectorDeposit` 树，显式保留零 hit primary；字段示例见
`config/examples/geant4_formal_input_fragment.json`。`geant4_legacy_root` 继续存在，
但只用于旧数据兼容和聚合检查。

能谱误差带使用 observed Fisher 信息对角近似，忽略联合单元协方差。方法名写入
摘要和 NPZ；它是快速诊断，不是完整覆盖率保证。

启用可视化时输出十三类图：全天 raw、前半球 raw/smoothed、正前方展示图、
平面投影、中心放大、能谱与误差、能段图、方向—能量联合图、收敛图、迭代快照、
事件核诊断和 dashboard。相机正前方来自配置的 -Z 来源方向。
