import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from Geant4RootInterface import Geant4RootInterface
from Geant4WindowBuilder import Geant4WindowBuilder
from Geant4EventSeparator import Geant4EventSeparator
from Geant4TruthLabelBuilder import Geant4TruthLabelBuilder
from Geant4TruthImager import Geant4TruthImager
from ComptonEventScorerV2 import ComptonEventScorerV2
from ComptonSupervisedTrainerV2 import ComptonSupervisedTrainerV2
from EventMatcher import EventMatcher
from ComptonConeImager import ComptonConeImager


PROGRAM_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT_PATH = PROGRAM_DIR.parent / "20260714_lyso.root"
OUTPUT_DIR = PROGRAM_DIR / "output_images" / "geant4_training"
MODEL_PATH = PROGRAM_DIR / "compton_scorer_v2_params.json"

# This is dataset truth used only to build supervised labels. It is never
# included in hit_df, candidate features, saved scorer parameters, or model
# imaging.  The separate oracle truth imager is allowed to use it.
FIXED_PRIMARY_ENERGY_MEV = 0.662
PRIMARY_ENERGY_MODE = "fixed"

CHAMBER_TO_LAYER = {
    0: 0,  # chamber 0 -> ch2, YSO, first scatter layer
    1: 1,  # ch1, YSO, second scatter layer
    2: 2,  # chamber 2 -> ch0, LYSO, absorber
}

ENERGY_FEATURE_MODE = "full"  # change to "normalized" for anti-shortcut QA
IMAGE_PLANE_Z = None  # set the known Geant4 source-plane z here when available
PLANE_DISTANCE_MM = 100.0


def _positive_weight(values):
    values = [int(value) for value in values if value is not None]
    positives = sum(values)
    negatives = len(values) - positives
    if positives == 0:
        return 1.0
    return max(1.0, negatives / float(positives))


def _print_binary_summary(name, labels, probabilities, threshold=0.5):
    pairs = [
        (int(label), float(probability))
        for label, probability in zip(labels, probabilities)
        if label is not None
    ]
    if not pairs:
        print(name + ": no labelled samples")
        return None

    y_true = np.asarray([pair[0] for pair in pairs], dtype=int)
    y_prob = np.asarray([pair[1] for pair in pairs], dtype=float)
    y_pred = (y_prob >= threshold).astype(int)

    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    precision = tp / float(tp + fp) if tp + fp else 0.0
    recall = tp / float(tp + fn) if tp + fn else 0.0
    brier = float(np.mean((y_prob - y_true) ** 2))

    print("========== " + name + " ==========")
    print("samples:", len(y_true), "positive:", int(y_true.sum()))
    print("TP/FP/FN/TN:", tp, fp, fn, tn)
    print("precision: {:.6f}".format(precision))
    print("recall   : {:.6f}".format(recall))
    print("brier    : {:.6f}".format(brier))
    return {
        "samples": int(len(y_true)),
        "positives": int(y_true.sum()),
        "precision": precision,
        "recall": recall,
        "brier": brier,
    }


def _build_candidates(hit_df, truth_df, seed):
    window_builder = Geant4WindowBuilder(
        hit_df=hit_df,
        event_ids_per_window=5,
        random_seed=seed,
    )
    windows = window_builder.build_windows()
    separator = Geant4EventSeparator(
        windows=windows,
        min_energy=0.0,
        allow_backscatter=False,
        sigma_delta_cos=0.15,
        max_candidates_per_window=None,
    )
    event_list = separator.separate()
    Geant4TruthLabelBuilder(event_list, truth_df).apply()
    return event_list


def _load_root_datasets(dataset_configs):
    all_hits = []
    all_truth = []

    for dataset_index, config in enumerate(dataset_configs):
        if isinstance(config, dict):
            root_path = Path(config["root_path"])
            primary_energy_mev = config.get(
                "primary_energy_mev",
                FIXED_PRIMARY_ENERGY_MEV,
            )
            primary_energy_mode = config.get(
                "primary_energy_mode",
                "fixed" if primary_energy_mev is not None else "branch",
            )
            dataset_id = config.get(
                "dataset_id",
                "dataset_{0:03d}".format(dataset_index),
            )
        else:
            root_path = Path(config)
            primary_energy_mev = FIXED_PRIMARY_ENERGY_MEV
            primary_energy_mode = PRIMARY_ENERGY_MODE
            dataset_id = "dataset_{0:03d}".format(dataset_index)

        if not root_path.exists():
            raise FileNotFoundError("找不到 ROOT 文件：" + str(root_path))

        interface = Geant4RootInterface(
            root_path=str(root_path),
            tree_name="Tree1",
            branch_map={
                "EventID": "eventID",
                "TotalEnergy": "eDep_MeV",
                "pos_x_mm": "x_post",
                "pos_y_mm": "y_post",
                "z": "z_post",
                "PixelID": "pixelID",
                "ChamberID": "chamberID",
            },
            chamber_to_layer=CHAMBER_TO_LAYER,
            primary_energy_mode=primary_energy_mode,
            fixed_primary_energy_mev=primary_energy_mev,
            strict_layer_assignment=True,
        )
        hit_df = interface.load()
        truth_df = interface.get_event_truth_df()
        interface.print_summary()

        event_map = {
            event_id: dataset_id + ":" + str(event_id)
            for event_id in hit_df["true_event_id"].unique()
        }
        hit_id_map = {
            hit_id: dataset_id + ":" + str(hit_id)
            for hit_id in hit_df["hit_id"].unique()
        }

        hit_df = hit_df.copy()
        hit_df["dataset_id"] = dataset_id
        hit_df["true_event_id"] = hit_df["true_event_id"].map(event_map)
        hit_df["hit_id"] = hit_df["hit_id"].map(hit_id_map)

        truth_df = truth_df.copy()
        truth_df["dataset_id"] = dataset_id
        truth_df["true_event_id"] = truth_df["true_event_id"].map(event_map)
        truth_df["visible_hit_ids"] = truth_df["visible_hit_ids"].apply(
            lambda values: tuple(hit_id_map[value] for value in values)
        )

        all_hits.append(hit_df)
        all_truth.append(truth_df)

    return (
        pd.concat(all_hits, ignore_index=True),
        pd.concat(all_truth, ignore_index=True),
    )


def _validate_truth_table(truth_df):
    if len(truth_df) == 0:
        raise RuntimeError("event_truth_df 为空，禁止继续训练。")

    primary = truth_df["primary_energy"]
    missing = int(primary.isna().sum())
    if missing > 0:
        raise RuntimeError(
            "有 " + str(missing) + " 个 true event 缺少 primary energy truth。"
        )

    source_counts = truth_df["primary_energy_source"].value_counts()
    full_values = truth_df["y_event_full"].dropna().astype(int)
    full_positive = int(full_values.sum())
    full_negative = int(len(full_values) - full_positive)

    print("========== Training Truth QA ==========")
    print("primary energy source:")
    print(source_counts)
    print("primary energy distribution:")
    print(primary.describe())
    print("event-full positive:", full_positive)
    print("event-full negative:", full_negative)
    print("=======================================")

    if full_positive == 0 or full_negative == 0:
        raise RuntimeError(
            "y_event_full 必须同时包含正负样本；当前标签不可用于训练。"
        )


def _validate_candidate_labels(event_list, name):
    match_values = [
        int(event.y_same_gamma)
        for event in event_list.events
        if event.y_same_gamma is not None
    ]
    full_values = [
        int(event.y_full_absorption)
        for event in event_list.events
        if event.y_same_gamma == 1 and event.y_full_absorption is not None
    ]
    order_sources = Counter(
        event.order_label_source for event in event_list.events
    )

    match_positive = sum(match_values)
    full_positive = sum(full_values)
    print("========== " + name + " Label QA ==========")
    print("candidates:", len(event_list))
    print("match positive/total:", match_positive, "/", len(match_values))
    print("full-absorption positive/total:", full_positive, "/", len(full_values))
    print("order label sources:", dict(order_sources))
    print("============================================")

    if match_positive == 0:
        raise RuntimeError(name + " 没有 match 正样本，禁止训练/评估。")
    if full_positive == 0:
        raise RuntimeError(name + " 没有 full-absorption 正样本，禁止继续。")


def _generate_direct_truth_image(hit_df, truth_df):
    truth_imager = Geant4TruthImager(
        hit_df=hit_df,
        truth_df=truth_df,
        output_dir=str(OUTPUT_DIR / "truth_imaging"),
        image_plane_z=IMAGE_PLANE_Z,
        plane_distance_mm=PLANE_DISTANCE_MM,
        x_range=(-150.0, 150.0),
        y_range=(-150.0, 150.0),
        n_pixels=200,
        sigma_angle_deg=5.0,
    )
    truth_event_list, paths = truth_imager.generate()
    print("direct truth imaging events:", len(truth_event_list))
    print("truth figures:")
    for path in paths:
        print(path)
    return truth_event_list


def main(root_paths=None, dataset_configs=None):
    if dataset_configs is None:
        if root_paths is None:
            root_paths = [DEFAULT_ROOT_PATH]
        elif isinstance(root_paths, (str, Path)):
            root_paths = [root_paths]
        dataset_configs = [
            {
                "dataset_id": "dataset_{0:03d}".format(index),
                "root_path": path,
                "primary_energy_mode": PRIMARY_ENERGY_MODE,
                "primary_energy_mev": FIXED_PRIMARY_ENERGY_MEV,
            }
            for index, path in enumerate(root_paths)
        ]

    hit_df, truth_df = _load_root_datasets(dataset_configs)
    _validate_truth_table(truth_df)

    # Independent oracle channel: no fake windows, scorer, matcher, or split.
    _generate_direct_truth_image(hit_df, truth_df)

    splitter = Geant4WindowBuilder(
        hit_df=hit_df,
        event_ids_per_window=5,
        random_seed=42,
    )
    train_hit_df, test_hit_df = splitter.split_train_test(train_ratio=0.8)

    train_event_list = _build_candidates(
        train_hit_df,
        truth_df,
        seed=1,
    )
    test_event_list = _build_candidates(
        test_hit_df,
        truth_df,
        seed=2,
    )
    print("train candidates:", len(train_event_list))
    print("test candidates :", len(test_event_list))
    _validate_candidate_labels(train_event_list, "train")
    _validate_candidate_labels(test_event_list, "test")

    train_match_labels = [
        event.y_same_gamma for event in train_event_list.events
    ]
    train_full_labels = [
        event.y_full_absorption
        for event in train_event_list.events
        if event.y_same_gamma == 1
    ]

    train_scorer = ComptonEventScorerV2(
        train_event_list,
        energy_feature_mode=ENERGY_FEATURE_MODE,
    )
    train_scorer.score_all_events()

    trainer = ComptonSupervisedTrainerV2(
        scorer=train_scorer,
        learning_rate=0.05,
        lambda_full=1.0,
        lambda_reg=1e-4,
        match_positive_weight=_positive_weight(train_match_labels),
        full_positive_weight=_positive_weight(train_full_labels),
    )
    trainer.fit(epochs=100, verbose=True)

    test_scorer = ComptonEventScorerV2(
        event_list=test_event_list,
        match_params=train_scorer.match_params.copy(),
        full_params=train_scorer.full_params.copy(),
        energy_feature_mode=ENERGY_FEATURE_MODE,
    )
    test_scorer.score_all_events()

    _print_binary_summary(
        "test same-gamma association",
        [event.y_same_gamma for event in test_event_list.events],
        [event.match_prob for event in test_event_list.events],
    )
    matched_truth_events = [
        event
        for event in test_event_list.events
        if event.y_same_gamma == 1 and event.y_full_absorption is not None
    ]
    _print_binary_summary(
        "test candidate full absorption",
        [event.y_full_absorption for event in matched_truth_events],
        [event.full_deposition_prob for event in matched_truth_events],
    )

    model_payload = {
        "model_version": 4,
        "feature_names": train_scorer.feature_names,
        "energy_feature_mode": ENERGY_FEATURE_MODE,
        "energy_scale_mev": train_scorer.energy_scale_mev,
        "distance_scale_mm": train_scorer.distance_scale_mm,
        "match_params": train_scorer.match_params,
        "full_params": train_scorer.full_params,
        "chamber_to_layer": CHAMBER_TO_LAYER,
    }
    with MODEL_PATH.open("w", encoding="utf-8") as file:
        json.dump(model_payload, file, indent=4, ensure_ascii=False)
    print("saved model:", MODEL_PATH)

    matcher = EventMatcher(test_event_list)
    matched_test_event_list = matcher.match()
    print("matched test events:", len(matched_test_event_list))

    imager = ComptonConeImager(
        event_list=matched_test_event_list,
        image_plane_z=IMAGE_PLANE_Z,
        plane_distance_mm=PLANE_DISTANCE_MM,
        x_range=(-150.0, 150.0),
        y_range=(-150.0, 150.0),
        n_pixels=200,
        sigma_angle_deg=5.0,
        min_score=0.05,
        output_dir=str(OUTPUT_DIR / "model_imaging"),
        known_primary_energy_mev=None,
    )
    paths = imager.save_all_diagnostic_plots()
    print("figures:")
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
