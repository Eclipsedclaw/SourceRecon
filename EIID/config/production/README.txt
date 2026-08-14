生产模板使用说明
================

1. 模板中的 REPLACE_* 必须替换为真实标定值或路径，不能直接用于物理分析。
2. response_build.template.json 中的 generation_area_cm2=100.0 只是明确可见的
   示例占位值，不是本相机的已确认生成平面面积。
3. 若使用有限距离响应，应把 normalization 改为：

   source_mode = finite_distance_restricted_solid_angle
   restricted_solid_angle_sr = 实际生成立体角
   source_distance_mm = 实际源距离

   构建器会计算 s_emitted=conditional*Omega/(4*pi)，不会把它与 A_eff 混用。
4. 只有独立验证完成后，才可把 library_status 从 candidate_unvalidated 改为
   validated_physical；EIID 会核对配置声明和响应库 manifest。
5. 每个数据集使用独立重建 JSON，再由 batch_manifest.template.json 汇总。
6. experiment_reconstruction.template.json 中 0 MeV 阈值、5 ns 符合窗、nside=16、
   0.05 MeV bin、迭代次数和能段都只是第一版默认建议；必须根据实验标定与
   小规模验证修改。它们没有被写入算法源码。
