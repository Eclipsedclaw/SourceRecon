import json
from pathlib import Path

from DataReader import DataReader
from DataPreProcessor import DataPreProcessor
from EventSeparator import EventSeparator
from ComptonEventScorerV2 import ComptonEventScorerV2
from EventMatcher import EventMatcher
from ComptonConeImager import ComptonConeImager


PROGRAM_DIR = Path(__file__).resolve().parent
MODEL_PATH = PROGRAM_DIR / "compton_scorer_v2_params.json"
OUTPUT_DIR = PROGRAM_DIR / "output_images" / "experiment"

# Fill these paths before running the experimental pipeline.
EXPERIMENT_PATHS = {
    "ch0_path": None,
    "ch1_path": None,
    "ch2_path": None,
    "calibration_ch0_path": None,
    "calibration_ch1_path": None,
    "calibration_ch2_path": None,
}


def _generate_experiment_image(event_list, output_subdirectory, stage_name):
    imager = ComptonConeImager(
        event_list=event_list,
        image_plane_z=None,
        plane_distance_mm=100.0,
        x_range=(-150.0, 150.0),
        y_range=(-150.0, 150.0),
        n_pixels=200,
        sigma_angle_deg=5.0,
        min_score=0.0,
        output_dir=str(OUTPUT_DIR / output_subdirectory),
        known_primary_energy_mev=None,
    )
    paths = imager.save_all_diagnostic_plots()
    print("========== " + stage_name + " Imaging ==========")
    print("input candidate events:", len(event_list))
    print("events with usable cone response:", len(imager.used_events))
    print("sum of imaging weights:", float(sum(imager.event_weights)))
    print("figures:")
    for path in paths:
        print(path)
    print("==============================================")
    return paths


def main(experiment_paths=None, model_path=None):
    experiment_paths = experiment_paths or EXPERIMENT_PATHS
    model_path = Path(model_path) if model_path is not None else MODEL_PATH

    if not model_path.exists():
        raise FileNotFoundError(
            "找不到训练参数。请先运行 main_geant4_train.py：" + str(model_path)
        )

    reader = DataReader(**experiment_paths)
    reader.read_data()
    final_df = DataPreProcessor(reader).build_final_df()

    separator = EventSeparator(
        final_df=final_df,
        channels=("ch2", "ch1", "ch0"),
        channel_to_layer={"ch2": 0, "ch1": 1, "ch0": 2},
        min_energy=0.0,
        allow_backscatter=False,
        sigma_delta_cos=0.15,
    )
    event_list = separator.separate()
    print("experimental candidates:", len(event_list))

    with model_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    scorer = ComptonEventScorerV2(
        event_list=event_list,
        match_params=payload["match_params"],
        full_params=payload["full_params"],
        energy_scale_mev=payload.get("energy_scale_mev", 1.0),
        distance_scale_mm=payload.get("distance_scale_mm", 100.0),
        energy_feature_mode=payload.get("energy_feature_mode", "full"),
        match_calibration=payload.get("match_calibration"),
        full_calibration=payload.get("full_calibration"),
        matching_probability_threshold=payload.get(
            "matching_probability_threshold",
            0.5,
        ),
    )
    scorer.score_all_events()

    _generate_experiment_image(
        event_list=event_list,
        output_subdirectory="before_match",
        stage_name="Before EventMatcher",
    )

    matcher = EventMatcher(
        event_list,
        min_match_probability=payload.get(
            "matching_probability_threshold",
            0.5,
        ),
    )
    matched_event_list = matcher.match()
    print("matched experimental events:", len(matched_event_list))

    _generate_experiment_image(
        event_list=matched_event_list,
        output_subdirectory="after_match",
        stage_name="After EventMatcher",
    )


if __name__ == "__main__":
    main()
