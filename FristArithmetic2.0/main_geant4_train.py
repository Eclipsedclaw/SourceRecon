# main_geant4_train.py

from Geant4RootInterface import Geant4RootInterface
from Geant4WindowBuilder import Geant4WindowBuilder
from Geant4EventSeparator import Geant4EventSeparator

from ComptonEventScorerV2 import ComptonEventScorerV2
from ComptonSupervisedTrainerV2 import ComptonSupervisedTrainerV2

from EventMatcher import EventMatcher
from ComptonConeImager import ComptonConeImager


def main():
    root_path = "/home/ezqi/labwork/SourceRecon/20260714_lyso.root"

    # ============================================================
    # 1. 读取 Geant4 ROOT
    # ============================================================

    interface = Geant4RootInterface(
        root_path=root_path,
        tree_name=None,
        branch_map=None,
    )

    hit_df = interface.load()
    interface.print_summary()

    # ============================================================
    # 2. 按 true_event_id 切 train/test
    # ============================================================

    splitter = Geant4WindowBuilder(
        hit_df=hit_df,
        event_ids_per_window=5,
        random_seed=42,
    )

    train_hit_df, test_hit_df = splitter.split_train_test(train_ratio=0.8)

    # ============================================================
    # 3. 构造 fake coincidence windows
    # ============================================================

    train_window_builder = Geant4WindowBuilder(
        hit_df=train_hit_df,
        event_ids_per_window=5,
        random_seed=1,
    )
    train_windows = train_window_builder.build_windows()

    test_window_builder = Geant4WindowBuilder(
        hit_df=test_hit_df,
        event_ids_per_window=5,
        random_seed=2,
    )
    test_windows = test_window_builder.build_windows()

    # ============================================================
    # 4. 枚举 candidate events
    # ============================================================

    train_separator = Geant4EventSeparator(
        windows=train_windows,
        min_energy=0.0,
        allow_backscatter=False,
        sigma_delta_cos=0.15,
        max_candidates_per_window=None,
    )
    train_event_list = train_separator.separate()

    test_separator = Geant4EventSeparator(
        windows=test_windows,
        min_energy=0.0,
        allow_backscatter=False,
        sigma_delta_cos=0.15,
        max_candidates_per_window=None,
    )
    test_event_list = test_separator.separate()

    print("train candidates:", len(train_event_list))
    print("test candidates:", len(test_event_list))

    train_df = train_event_list.to_dataframe()
    print(train_df[["event_type", "y_match", "y_full", "E_total", "score"]].head())

    print("train y_match positive:", train_df["y_match"].sum())
    print("train y_match total:", train_df["y_match"].notna().sum())

    # ============================================================
    # 5. 训练双头 scorer
    # ============================================================

    train_scorer = ComptonEventScorerV2(train_event_list)
    train_scorer.score_all_events()

    trainer = ComptonSupervisedTrainerV2(
        scorer=train_scorer,
        learning_rate=0.05,
        lambda_full=1.0,
        lambda_reg=1e-4,
    )

    trainer.fit(
        epochs=100,
        verbose=True,
    )

    # ============================================================
    # 6. 测试集打分
    # ============================================================

    test_scorer = ComptonEventScorerV2(
        event_list=test_event_list,
        match_params=train_scorer.match_params.copy(),
        full_params=train_scorer.full_params.copy(),
    )
    test_scorer.score_all_events()

    # ============================================================
    # 7. matching
    # ============================================================

    matcher = EventMatcher(test_event_list)
    matched_test_event_list = matcher.match()

    print("matched test events:", len(matched_test_event_list))

    # ============================================================
    # 8. 成像
    # ============================================================

    imager = ComptonConeImager(
        event_list=matched_test_event_list,
        image_plane_z=None,
        plane_distance_mm=100.0,
        x_range=(-150.0, 150.0),
        y_range=(-150.0, 150.0),
        n_pixels=200,
        sigma_angle_deg=5.0,
        min_score=0.05,
        output_dir="figure/geant4_v2_imaging",
    )

    paths = imager.save_all_diagnostic_plots()

    print("figures:")
    for p in paths:
        print(p)


if __name__ == "__main__":
    main()