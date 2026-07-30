# TwoHitEvent.py

import numpy as np


class TwoHitEvent:
    """
    单个 2-hit 康普顿候选事件。

    这个类只保存候选的可观测物理量。Geant4 标签由外部构造器注入。
    """

    MEC2_MEV = 0.51099895

    def __init__(self, event_id, hit1, hit2):
        self.event_id = event_id

        self.hit1 = hit1
        self.hit2 = hit2

        self.n_hits = 2
        self.event_type = "2hit"

        self.hit_ids = [hit1["hit_id"], hit2["hit_id"]]
        self.channels = [hit1.get("channel", None), hit2.get("channel", None)]
        self.layers = [hit1.get("layer", None), hit2.get("layer", None)]
        self.pixelids = [hit1.get("pixelid", None), hit2.get("pixelid", None)]

        self.r1 = hit1["pos"]
        self.r2 = hit2["pos"]

        self.E1 = float(hit1["energy"])
        self.E2 = float(hit2["energy"])
        self.E_total = self.E1 + self.E2

        self.distance_12 = self._distance(self.r1, self.r2)

        # 这个角度只在“全能量沉积”假设下可靠
        self.cos_theta_c = self._calculate_compton_cos_from_deposited_energy()
        self.theta_c = self._calculate_theta_from_cos(self.cos_theta_c)

        self.is_physical = self._check_physical_validity()

        # Geant4 truth 信息
        self.true_event_ids = self._collect_true_event_ids()
        # Geant4 truth labels are attached later by
        # Geant4TruthLabelBuilder. Keeping truth out of the physics object
        # prevents primary energy from leaking into model features.
        self.primary_energies = []
        self.y_same_gamma = self._build_y_match()
        self.y_correct_order = None
        self.y_match_correct = None
        self.y_event_full = None
        self.y_candidate_complete = None
        self.y_full_absorption = None
        self.y_complete_full = None
        self.order_label_source = None

        # Backward-compatible aliases. The label builder overwrites these with
        # their stricter definitions during Geant4 training.
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

    def _calculate_compton_cos_from_deposited_energy(self):
        """
        2-hit 默认全沉积假设：
            E_before = E1 + E2
            E_after = E2

        注意：
            对 escape event，这个角度不可靠。
            后面要由 full_deposition_prob gate 控制是否使用。
        """

        if self.E_total <= 0 or self.E2 <= 0:
            return np.nan

        return float(
            1.0
            - self.MEC2_MEV * (1.0 / self.E2 - 1.0 / self.E_total)
        )

    def _calculate_theta_from_cos(self, cos_value):
        if np.isnan(cos_value):
            return np.nan
        if cos_value < -1.0 or cos_value > 1.0:
            return np.nan
        return float(np.arccos(cos_value))

    def _check_physical_validity(self):
        if np.isnan(self.cos_theta_c):
            return False
        return -1.0 <= self.cos_theta_c <= 1.0

    def _collect_true_event_ids(self):
        ids = []
        for hit in [self.hit1, self.hit2]:
            ids.append(hit.get("true_event_id", None))
        return ids

    def _build_y_match(self):
        """
        Geant4 监督标签：
            两个 hit 的 true_event_id 相同 → y_match = 1
            否则 → y_match = 0

        如果没有 truth 信息，则返回 None。
        """

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
            "E3": None,
            "E_total": self.E_total,

            "r1": self.r1,
            "r2": self.r2,
            "r3": None,

            "distance_12": self.distance_12,
            "distance_23": None,

            "cos_theta_c": self.cos_theta_c,
            "theta_c": self.theta_c,

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
