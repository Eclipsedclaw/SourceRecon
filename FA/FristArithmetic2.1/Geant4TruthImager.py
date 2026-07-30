from collections import Counter

import numpy as np

from ComptonConeImager import ComptonConeImager
from EventList import EventList
from ThreeHitEvent import ThreeHitEvent
from TwoHitEvent import TwoHitEvent


class Geant4TruthImager:
    """Build an oracle image directly from Geant4 event truth.

    This path never uses fake coincidence windows, model scores, matching, or
    train/test labels.  Hits are grouped by their original Geant4 event ID.
    Only two-hit and three-hit events whose hits occupy different detector
    layers are retained.  With back-scattering disabled, layer order defines
    the interaction order.

    The known simulated primary energy is used only here to calculate the
    oracle first-scatter angle.  It is not copied into training features.
    """

    MEC2_MEV = 0.51099895

    def __init__(
        self,
        hit_df,
        truth_df,
        output_dir,
        image_plane_z=None,
        plane_distance_mm=100.0,
        x_range=(-150.0, 150.0),
        y_range=(-150.0, 150.0),
        n_pixels=200,
        sigma_angle_deg=5.0,
        energy_tolerance_mev=0.03,
    ):
        self.hit_df = hit_df
        self.truth_df = truth_df
        self.output_dir = output_dir
        self.image_plane_z = image_plane_z
        self.plane_distance_mm = plane_distance_mm
        self.x_range = x_range
        self.y_range = y_range
        self.n_pixels = n_pixels
        self.sigma_angle_deg = sigma_angle_deg
        self.energy_tolerance_mev = energy_tolerance_mev

        self.event_list = EventList()
        self.summary = Counter()

    def build_event_list(self):
        primary_by_event = self._primary_energy_lookup()
        event_list = EventList()
        summary = Counter()

        for true_event_id, group in self.hit_df.groupby(
            "true_event_id",
            sort=False,
        ):
            summary["original_event_ids"] += 1
            group = group.sort_values("layer", kind="stable")
            n_hits = int(len(group))

            if n_hits not in (2, 3):
                summary["excluded_not_2_or_3_hits"] += 1
                continue

            layers = group["layer"].astype(int).tolist()
            if len(set(layers)) != n_hits:
                summary["excluded_repeated_layer"] += 1
                continue

            primary_energy = primary_by_event.get(true_event_id, np.nan)
            if np.isnan(primary_energy) or primary_energy <= 0.0:
                summary["excluded_missing_primary_energy"] += 1
                continue

            hits = [self._row_to_hit(row) for _, row in group.iterrows()]
            if n_hits == 2:
                event = TwoHitEvent(
                    event_id="truth:" + str(true_event_id),
                    hit1=hits[0],
                    hit2=hits[1],
                )
                summary["two_hit_events"] += 1
            else:
                event = ThreeHitEvent(
                    event_id="truth:" + str(true_event_id),
                    hit1=hits[0],
                    hit2=hits[1],
                    hit3=hits[2],
                )
                summary["three_hit_events"] += 1

            if not self._set_oracle_first_scatter_angle(
                event,
                float(primary_energy),
            ):
                summary["excluded_invalid_oracle_angle"] += 1
                continue

            event.truth_primary_energy_mev = float(primary_energy)
            event.truth_energy_complete = int(
                abs(float(event.E_total) - float(primary_energy))
                < self.energy_tolerance_mev
            )
            if event.truth_energy_complete == 1:
                summary["energy_complete_events"] += 1
            else:
                summary["energy_escape_events"] += 1

            # Oracle events have known association.  Unit weight keeps the
            # truth image independent of the learned scorer.
            event.y_same_gamma = 1
            event.y_match_correct = 1
            event.y_full_absorption = event.truth_energy_complete
            event.match_prob = 1.0
            event.full_deposition_prob = 1.0
            event.matching_score = 1.0
            event.imaging_weight = 1.0
            event.score = 1.0
            event_list.add_event(event)
            summary["imaging_events"] += 1

        self.event_list = event_list
        self.summary = summary
        self._print_summary()
        return event_list

    def generate(self):
        event_list = self.build_event_list()
        if len(event_list) == 0:
            raise RuntimeError(
                "没有可用于真值成像的跨层2-hit/3-hit Geant4事件。"
            )

        imager = ComptonConeImager(
            event_list=event_list,
            image_plane_z=self.image_plane_z,
            plane_distance_mm=self.plane_distance_mm,
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

    def _set_oracle_first_scatter_angle(self, event, primary_energy):
        first_deposition = float(event.E1)
        scattered_energy = primary_energy - first_deposition
        if primary_energy <= 0.0 or scattered_energy <= 0.0:
            return False

        cos_theta = 1.0 - self.MEC2_MEV * (
            1.0 / scattered_energy - 1.0 / primary_energy
        )
        if cos_theta < -1.0 or cos_theta > 1.0:
            return False

        theta = float(np.arccos(cos_theta))
        if event.n_hits == 2:
            event.cos_theta_c = float(cos_theta)
            event.theta_c = theta
        else:
            event.cos_theta_c_first = float(cos_theta)
            event.theta_c_first = theta
        return True

    def _print_summary(self):
        print("========== Direct Geant4 Truth Imaging ==========")
        ordered_keys = [
            "original_event_ids",
            "excluded_not_2_or_3_hits",
            "excluded_repeated_layer",
            "excluded_missing_primary_energy",
            "excluded_invalid_oracle_angle",
            "two_hit_events",
            "three_hit_events",
            "energy_complete_events",
            "energy_escape_events",
            "imaging_events",
        ]
        for key in ordered_keys:
            print(key + ":", int(self.summary.get(key, 0)))
        print("==================================================")
