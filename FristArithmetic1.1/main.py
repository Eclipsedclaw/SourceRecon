# main.py

# =========================================================
# 物理管线（无监督版）
#
# 适用于当前阶段：真实测量数据、没有 MC 真值。
#
# 流程：
#   1. 读取数据、预处理
#   2. 定义探测器分辨率模型（必须先用刻度数据填参数！）
#   3. EventSeparator 分事件
#      （ThreeHitEvent 构造时自动完成误差传播 + pull 打分）
#   4. MixedEventBackground 混合本底：
#      验证 pull 鉴别路线可行性、定量选切割阈值
#   5. EventMatcher 全局匹配
#   6. ComptonConeImager 成像（默认只用 3-hit）
#      + 调焦扫描找源平面
#
# 注意：
#   本管线不做任何监督训练。
#   ComptonEventScorer / ComptonGradientTrainer 留给
#   宽谱 Geant4 MC 数据到位后的阶段 B。
# =========================================================

from DataReader import DataReader
from DataPreProcessor import DataPreProcessor

from DetectorResolution import DetectorResolutionModel
from EventSeparator import EventSeparator
from MixedEventBackground import MixedEventBackground
from EventMatcher import EventMatcher
from ComptonConeImager import ComptonConeImager


def run_physics_pipeline():
    # ============================================================
    # 1. 读取数据
    # ============================================================

    reader = DataReader()
    reader.read_data()

    preprocessor = DataPreProcessor(reader)
    final_df = preprocessor.build_final_df()

    print("final_df shape:", final_df.shape)

    # ============================================================
    # 2. 探测器分辨率模型
    #
    # !!! 这里的参数是占位值，必须替换 !!!
    #
    # 方式一：直接填
    #   energy_a / energy_b: 用刻度峰拟合 sigma_E = a*sqrt(E) + b
    #   sigma_pos_mm: 像素间距 / sqrt(12)
    #
    # 方式二：用刻度峰自动拟合（推荐）
    #   resolution_model = DetectorResolutionModel.from_calibration_points(
    #       peak_energies_mev=[0.122, 0.511, 0.662],   # 你的刻度峰
    #       peak_sigmas_mev=[...],                      # 对应峰的 sigma（不是FWHM）
    #       sigma_pos_mm=1.5,
    #   )
    # ============================================================

    resolution_model = DetectorResolutionModel(
        energy_a=0.010,      # TODO: 替换为你的刻度拟合值
        energy_b=0.002,      # TODO: 替换为你的刻度拟合值
        sigma_pos_mm=1.5,    # TODO: 替换为 像素间距/sqrt(12)
        sigma_delta_floor=0.02,
    )

    print("resolution model:", resolution_model)

    # ============================================================
    # 3. 分事件
    #
    # min_energy 设为真实噪声阈值（MeV）。
    # 低能噪声 hit 会污染 E_total 并制造假 3-hit。
    # ============================================================

    separator = EventSeparator(
        final_df=final_df,
        min_energy=0.02,     # TODO: 按你探测器的噪声水平调整
        allow_backscatter=False,
        resolution_model=resolution_model,
    )

    event_list = separator.separate()

    n_2hit = len(event_list.get_two_hit_events())
    n_3hit = len(event_list.get_three_hit_events())

    print(f"event 总数: {len(event_list)} (2-hit: {n_2hit}, 3-hit: {n_3hit})")

    # ============================================================
    # 4. 混合事件本底：pull 鉴别路线的可行性判定
    #
    # 关键判读：
    #   figure/mixed_background/pull_real_vs_mixed.png
    #   实测 pull 在 0 附近的峰能否从混合本底平台中立起来。
    #   立得起来 → 路线可行，按 pass rate 曲线选阈值；
    #   完全重合 → 数据里几乎没有可用的真 3-hit，
    #              先回头检查能量刻度 / 噪声阈值。
    # ============================================================

    background = MixedEventBackground(
        final_df=final_df,
        resolution_model=resolution_model,
        min_energy=0.02,     # 与 separator 保持一致
        n_fake=20000,
        output_dir="figure/mixed_background",
    )

    background.build()
    background.plot_comparison(event_list)
    background.plot_pass_rate_scan(event_list)
    background.print_summary(event_list)

    # ============================================================
    # 5. 全局匹配
    #
    # event 的 score 已在构造时按 pull 解析计算，
    # matcher 直接用它消解 hit 冲突。
    # ============================================================

    matcher = EventMatcher(event_list)
    matched_event_list = matcher.match()

    print("matching 后 event 数量:", len(matched_event_list))

    # ============================================================
    # 6. 成像（默认只用 3-hit）
    #
    # min_score 与 |pull| 的换算：
    #   0.61 ~ |pull|<1   0.14 ~ |pull|<2   0.011 ~ |pull|<3
    #
    # 建议先用 0.14（|pull|<2），
    # 结合混合本底的 pass rate 曲线再微调。
    # ============================================================

    imager = ComptonConeImager(
        event_list=matched_event_list,

        image_plane_z=None,
        plane_distance_mm=100.0,
        x_range=(-150.0, 150.0),
        y_range=(-150.0, 150.0),
        n_pixels=200,

        sigma_angle_deg=5.0,

        min_score=0.14,          # ~ |pull| < 2
        include_two_hit=False,   # 2-hit 等 MC 门控就绪后再打开
        normalize_response=True,

        output_dir="figure/physics_pipeline_imaging",
    )

    figure_paths = imager.save_all_diagnostic_plots()

    print("输出图像：")
    for path in figure_paths:
        print(path)

    # ============================================================
    # 7. 调焦扫描：找源所在平面
    #
    # 峰均比最大的距离 = 源的真实距离。
    # 如果曲线整体平坦（峰均比始终接近 1），
    # 说明环没有公共交点：
    #   要么 z 方向假设反了（把 _auto_set_image_plane_z 的
    #   减号方向反过来再扫一遍），
    #   要么通过筛选的事件仍然质量不足。
    # ============================================================

    best_d, best_z, distances, metrics = imager.scan_plane_distance(
        d_min=20.0,
        d_max=300.0,
        n_planes=15,
    )

    print(f"最佳聚焦距离: {best_d:.0f} mm (z = {best_z:.1f} mm)")


if __name__ == "__main__":
    run_physics_pipeline()