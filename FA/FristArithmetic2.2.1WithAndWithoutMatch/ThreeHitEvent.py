# ThreeHitEvent.py

import numpy as np


class ThreeHitEvent:
    """
    单个 3-hit 康普顿候选事件。

    只保存候选的可观测物理量。Geant4 标签由外部构造器注入。
    """

    MEC2_MEV = 0.51099895

    def __init__(self, event_id, hit1, hit2, hit3, sigma_delta_cos=0.15):
        self.event_id = event_id

        self.hit1 = hit1
        self.hit2 = hit2
        self.hit3 = hit3

        self.n_hits = 3
        self.event_type = "3hit"
        self.sigma_delta_cos = sigma_delta_cos

        self.hit_ids = [hit1["hit_id"], hit2["hit_id"], hit3["hit_id"]]
        self.channels = [
            hit1.get("channel", None),
            hit2.get("channel", None),
            hit3.get("channel", None),
        ]
        self.layers = [
            hit1.get("layer", None),
            hit2.get("layer", None),
            hit3.get("layer", None),
        ]
        self.pixelids = [
            hit1.get("pixelid", None),
            hit2.get("pixelid", None),
            hit3.get("pixelid", None),
        ]

        self.r1 = hit1["pos"]
        self.r2 = hit2["pos"]
        self.r3 = hit3["pos"]

        self.E1 = float(hit1["energy"])
        self.E2 = float(hit2["energy"])
        self.E3 = float(hit3["energy"])
        self.E_total = self.E1 + self.E2 + self.E3

        self.distance_12 = self._distance(self.r1, self.r2)
        self.distance_23 = self._distance(self.r2, self.r3)

        # 这些角度都基于“全能量沉积”假设
        self.cos_theta_c_first = self._calculate_first_compton_cos()
        self.theta_c_first = self._calculate_theta_from_cos(
            self.cos_theta_c_first
        )

        self.cos_theta_c_second = self._calculate_second_compton_cos()
        self.cos_theta_g_second = self._calculate_second_geometry_cos()
        self.delta_cos_second = self._calculate_delta_cos_second()

        self.is_physical = self._check_physical_validity()

        # Geant4 truth
        self.true_event_ids = self._collect_true_event_ids()
        self.primary_energies = []
        self.y_same_gamma = self._build_y_match()
        self.y_correct_order = None
        self.y_match_correct = None
        self.y_event_full = None
        self.y_candidate_complete = None
        self.y_full_absorption = None
        self.y_complete_full = None
        self.order_label_source = None

        self.y_match = self.y_same_gamma
        self.y_full = None
        self.y_usable = None

        # 初始分数，后面由 scorer 覆盖
        self.score = 0.0
        self.match_prob = 0.0
        self.full_deposition_prob = 0.0
        self.imaging_weight = 0.0
        self.matching_score = 0.0

    def _distance(self, r_a, r_b):
        return float(np.linalg.norm(r_b - r_a))

    def _calculate_theta_from_cos(self, cos_value):
        if np.isnan(cos_value):
            return np.nan
        if cos_value < -1.0 or cos_value > 1.0:
            return np.nan
        return float(np.arccos(cos_value))

    def _calculate_first_compton_cos(self):
        """
        第一次散射角，全沉积假设下：
            E_before = E1 + E2 + E3
            E_after = E2 + E3
        """

        e_before = self.E_total
        e_after = self.E2 + self.E3

        if e_before <= 0 or e_after <= 0:
            return np.nan

        return float(
            1.0
            - self.MEC2_MEV * (1.0 / e_after - 1.0 / e_before)
        )

    def _calculate_second_compton_cos(self):
        """
        第二次散射角，全沉积假设下：
            E_before = E2 + E3
            E_after = E3
        """

        e_before = self.E2 + self.E3
        e_after = self.E3

        if e_before <= 0 or e_after <= 0:
            return np.nan

        return float(
            1.0
            - self.MEC2_MEV * (1.0 / e_after - 1.0 / e_before)
        )

    def _calculate_second_geometry_cos(self):
        v_in = self.r2 - self.r1
        v_out = self.r3 - self.r2

        norm_in = np.linalg.norm(v_in)
        norm_out = np.linalg.norm(v_out)

        if norm_in == 0 or norm_out == 0:
            return np.nan

        return float(np.dot(v_in, v_out) / (norm_in * norm_out))

    def _calculate_delta_cos_second(self):
        if np.isnan(self.cos_theta_c_second):
            return np.nan
        if np.isnan(self.cos_theta_g_second):
            return np.nan

        return float(self.cos_theta_c_second - self.cos_theta_g_second)

    def _valid_cos(self, value):
        if np.isnan(value):
            return False
        return -1.0 <= value <= 1.0

    def _check_physical_validity(self):
        return (
            self._valid_cos(self.cos_theta_c_first)
            and self._valid_cos(self.cos_theta_c_second)
            and self._valid_cos(self.cos_theta_g_second)
        )

    def _collect_true_event_ids(self):
        ids = []
        for hit in [self.hit1, self.hit2, self.hit3]:
            ids.append(hit.get("true_event_id", None))
        return ids

    def _build_y_match(self):
        if any(v is None for v in self.true_event_ids):
            return None

        return int(len(set(self.true_event_ids)) == 1)

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "n_hits": self.n_hits,

            "hit_ids": self.hit_ids,
            "channels": self.channels,
            "layers": self.layers,
            "pixelids": self.pixelids,

            "E1": self.E1,
            "E2": self.E2,
            "E3": self.E3,
            "E_total": self.E_total,

            "r1": self.r1,
            "r2": self.r2,
            "r3": self.r3,

            "distance_12": self.distance_12,
            "distance_23": self.distance_23,

            "cos_theta_c_first": self.cos_theta_c_first,
            "theta_c_first": self.theta_c_first,

            "cos_theta_c_second": self.cos_theta_c_second,
            "cos_theta_g_second": self.cos_theta_g_second,
            "delta_cos_second": self.delta_cos_second,

            "is_physical": self.is_physical,

            "true_event_ids": self.true_event_ids,
            "primary_energies": self.primary_energies,
            "y_match": self.y_match,
            "y_same_gamma": self.y_same_gamma,
            "y_correct_order": self.y_correct_order,
            "y_match_correct": self.y_match_correct,
            "y_event_full": self.y_event_full,
            "y_candidate_complete": self.y_candidate_complete,
            "y_full_absorption": self.y_full_absorption,
            "y_complete_full": self.y_complete_full,
            "order_label_source": self.order_label_source,
            "y_full": self.y_full,
            "y_usable": self.y_usable,

            "score": self.score,
            "match_prob": self.match_prob,
            "full_deposition_prob": self.full_deposition_prob,
            "imaging_weight": self.imaging_weight,
            "matching_score": self.matching_score,
        }
