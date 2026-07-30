import itertools
from collections import Counter

import numpy as np

from ComptonConeImager import ComptonConeImager
from EventList import EventList
from ThreeHitEvent import ThreeHitEvent
from TwoHitEvent import TwoHitEvent


class Geant4TruthImager:
    """Build an oracle image directly from Geant4 event truth.

    Pixel hits are first grouped by their original Geant4 event ID.  Every
    two-hit or three-hit combination whose hits occupy different detector
    layers is considered, even when the original event contains additional
    pixel hits.  This maximizes use of truth data without merging different
    pixels.

    Primary-gamma ``Process_post`` history validates the required number of
    Compton interactions.  Three-hit combinations must also satisfy their
    second-scatter energy/geometry consistency.
    """

    MEC2_MEV = 0.51099895

    def __init__(
        self,
        hit_df,
        truth_df,
        raw_step_df,
        output_dir,
        image_plane_z,
        x_range=(-150.0, 150.0),
        y_range=(-150.0, 150.0),
        n_pixels=200,
        sigma_angle_deg=5.0,
        energy_tolerance_mev=0.03,
        max_abs_delta_cos_second=0.15,
    ):
        self.hit_df = hit_df
        self.truth_df = truth_df
        self.raw_step_df = raw_step_df
        self.output_dir = output_dir
        self.image_plane_z = image_plane_z
        self.x_range = x_range
        self.y_range = y_range
        self.n_pixels = n_pixels
        self.sigma_angle_deg = sigma_angle_deg
        self.energy_tolerance_mev = energy_tolerance_mev
        self.max_abs_delta_cos_second = max_abs_delta_cos_second

        self.event_list = EventList()
        self.summary = Counter()

    def build_event_list(self):
        primary_by_event = self._primary_energy_lookup()
        compton_count_by_event = self._primary_compton_count_lookup()
        event_list = EventList()
        summary = Counter()

        for true_event_id, group in self.hit_df.groupby(
            "true_event_id",
            sort=False,
        ):
            summary["original_event_ids"] += 1
            rows = [row for _, row in group.iterrows()]
            distinct_layers = set(int(row["layer"]) for row in rows)
            if len(distinct_layers) < 2:
                summary["excluded_no_cross_layer_pair"] += 1
                continue

            summary["event_ids_with_cross_layer_hits"] += 1
            primary_energy = primary_by_event.get(true_event_id, np.nan)
            if np.isnan(primary_energy) or primary_energy <= 0.0:
                summary["excluded_missing_primary_energy"] += 1
                continue

            compton_count = compton_count_by_event.get(true_event_id, 0)
            for row_a, row_b in itertools.combinations(rows, 2):
                if int(row_a["layer"]) == int(row_b["layer"]):
                    continue
                summary["two_hit_combinations"] += 1
                if compton_count < 1:
                    summary["excluded_2hit_process_truth"] += 1
                    continue

                ordered = sorted(
                    [row_a, row_b],
                    key=lambda row: int(row["layer"]),
                )
                event = TwoHitEvent(
                    event_id="truth:" + str(true_event_id),
                    hit1=self._row_to_hit(ordered[0]),
                    hit2=self._row_to_hit(ordered[1]),
                )
                if not self._set_oracle_angles(event, float(primary_energy)):
                    summary["excluded_invalid_first_angle"] += 1
                    continue
                self._prepare_oracle_event(event, primary_energy, summary)
                event_list.add_event(event)
                summary["two_hit_imaging_events"] += 1

            for selected_rows in itertools.combinations(rows, 3):
                layers = [int(row["layer"]) for row in selected_rows]
                if len(set(layers)) != 3:
                    continue
                summary["three_hit_combinations"] += 1
                if compton_count < 2:
                    summary["excluded_3hit_process_truth"] += 1
                    continue

                ordered = sorted(
                    selected_rows,
                    key=lambda row: int(row["layer"]),
                )
                event = ThreeHitEvent(
                    event_id="truth:" + str(true_event_id),
                    hit1=self._row_to_hit(ordered[0]),
                    hit2=self._row_to_hit(ordered[1]),
                    hit3=self._row_to_hit(ordered[2]),
                )
                if not self._set_oracle_angles(event, float(primary_energy)):
                    summary["excluded_invalid_first_angle"] += 1
                    continue
                if (
                    np.isnan(event.delta_cos_second)
                    or abs(event.delta_cos_second)
                    > self.max_abs_delta_cos_second
                ):
                    summary["excluded_invalid_second_scatter"] += 1
                    continue

                self._prepare_oracle_event(event, primary_energy, summary)
                event_list.add_event(event)
                summary["three_hit_imaging_events"] += 1

        summary["imaging_events"] = len(event_list)
        self.event_list = event_list
        self.summary = summary
        self._print_summary()
        return event_list

    def generate(self):
        event_list = self.build_event_list()
        if len(event_list) == 0:
            raise RuntimeError(
                "没有通过Geant4过程与康普顿物理检查的跨层真值事件。"
            )

        imager = ComptonConeImager(
            event_list=event_list,
            image_plane_z=self.image_plane_z,
            plane_distance_mm=100.0,
            x_range=self.x_range,
            y_range=self.y_range,
            n_pixels=self.n_pixels,
            sigma_angle_deg=self.sigma_angle_deg,
            min_score=0.0,
            output_dir=str(self.output_dir),
            known_primary_energy_mev=None,
        )
        paths = imager.save_all_diagnostic_plots()
        return event_list, paths

    def _primary_energy_lookup(self):
        lookup = {}
        for _, row in self.truth_df.iterrows():
            lookup[row["true_event_id"]] = float(row["primary_energy"])
        return lookup

    def _primary_compton_count_lookup(self):
        counts = {}
        if self.raw_step_df is None or len(self.raw_step_df) == 0:
            return counts

        required = {
            "true_event_id",
            "parent_id",
            "particle_name",
            "process_post",
        }
        if not required.issubset(self.raw_step_df.columns):
            raise RuntimeError(
                "真值成像需要 parentID、particleName 和 Process_post。"
            )

        steps = self.raw_step_df
        primary = steps[steps["parent_id"] == 0].copy()
        names = primary["particle_name"].astype(str).str.lower()
        primary = primary[names.str.contains("gamma", na=False)]
        processes = primary["process_post"].astype(str).str.lower()
        primary = primary[
            processes.str.contains("compt", na=False)
            | processes.str.contains("compton", na=False)
        ]
        if len(primary) == 0:
            raise RuntimeError(
                "Process_post 中没有找到初级gamma的Compton过程；"
                "请检查ROOT过程名称。"
            )
        for event_id, group in primary.groupby("true_event_id", sort=False):
            counts[event_id] = int(len(group))
        return counts

    @staticmethod
    def _row_to_hit(row):
        return {
            "true_event_id": row["true_event_id"],
            "hit_id": row["hit_id"],
            "layer": int(row["layer"]),
            "channel": row.get("channel", None),
            "pixelid": row.get("pixelid", None),
            "x": float(row["x"]),
            "y": float(row["y"]),
            "z": float(row["z"]),
            "pos": np.array(
                [float(row["x"]), float(row["y"]), float(row["z"])],
                dtype=float,
            ),
            "energy": float(row["energy"]),
            "first_time_ns": row.get("first_time_ns", np.nan),
            "first_step_id": row.get("first_step_id", np.nan),
            "material": row.get("material", None),
            "chamberid": row.get("chamberid", np.nan),
        }

    def _set_oracle_angles(self, event, primary_energy):
        first_before = primary_energy
        first_after = first_before - float(event.E1)
        first_cos = self._compton_cos(first_before, first_after)
        if np.isnan(first_cos):
            return False

        first_theta = float(np.arccos(first_cos))
        if event.n_hits == 2:
            event.cos_theta_c = float(first_cos)
            event.theta_c = first_theta
            event.is_physical = True
            return True

        event.cos_theta_c_first = float(first_cos)
        event.theta_c_first = first_theta
        second_before = first_after
        second_after = second_before - float(event.E2)
        second_cos = self._compton_cos(second_before, second_after)
        if np.isnan(second_cos):
            return False
        event.cos_theta_c_second = float(second_cos)
        event.delta_cos_second = float(
            second_cos - event.cos_theta_g_second
        )
        event.is_physical = True
        return True

    def _compton_cos(self, energy_before, energy_after):
        if energy_before <= 0.0 or energy_after <= 0.0:
            return np.nan
        value = 1.0 - self.MEC2_MEV * (
            1.0 / energy_after - 1.0 / energy_before
        )
        if value < -1.0 or value > 1.0:
            return np.nan
        return float(value)

    def _prepare_oracle_event(self, event, primary_energy, summary):
        event.truth_primary_energy_mev = float(primary_energy)
        event.truth_energy_complete = int(
            abs(float(event.E_total) - float(primary_energy))
            < self.energy_tolerance_mev
        )
        if event.truth_energy_complete == 1:
            summary["energy_complete_events"] += 1
        else:
            summary["energy_escape_events"] += 1

        event.is_oracle_truth = True
        event.y_same_gamma = 1
        event.y_match_correct = 1
        event.y_full_absorption = event.truth_energy_complete
        event.match_prob = 1.0
        event.full_deposition_prob = 1.0
        event.matching_score = 1.0
        event.imaging_weight = 1.0
        event.score = 1.0

    def _print_summary(self):
        print("========== Direct Geant4 Truth Imaging ==========")
        ordered_keys = [
            "original_event_ids",
            "excluded_no_cross_layer_pair",
            "event_ids_with_cross_layer_hits",
            "two_hit_combinations",
            "excluded_2hit_process_truth",
            "two_hit_imaging_events",
            "three_hit_combinations",
            "excluded_3hit_process_truth",
            "excluded_invalid_first_angle",
            "excluded_invalid_second_scatter",
            "three_hit_imaging_events",
            "energy_complete_events",
            "energy_escape_events",
            "imaging_events",
        ]
        for key in ordered_keys:
            print(key + ":", int(self.summary.get(key, 0)))
        print("==================================================")
