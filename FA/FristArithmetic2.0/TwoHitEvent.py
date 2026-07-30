# TwoHitEvent.py

import numpy as np


class TwoHitEvent:
    """
    单个 2-hit 康普顿候选事件。

    这个类现在同时支持：
        1. 实验数据：没有 truth label
        2. Geant4 数据：hit 中带 true_event_id / primary_energy，可自动生成监督标签
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
        self.primary_energies = self._collect_primary_energies()

        self.y_match = self._build_y_match()
        self.y_full = self._build_y_full()
        self.y_usable = self._build_y_usable()

        # 初始分数，后面由 scorer 覆盖
        self.score = 0.0
        self.match_prob = 0.0
        self.full_deposition_prob = 0.0
        self.imaging_weight = 0.0

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

    def _collect_primary_energies(self):
        energies = []
        for hit in [self.hit1, self.hit2]:
            energies.append(hit.get("primary_energy", None))
        return energies

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

    def _build_y_full(self, energy_tolerance_mev=0.03):
        """
        判断是否全能量沉积。

        只对 y_match=1 的 candidate 有意义。

        如果 primary_energy 可用：
            abs(E_total - primary_energy) < tolerance → 1
        否则返回 None。
        """

        if self.y_match != 1:
            return None

        valid_primary = [
            e for e in self.primary_energies
            if e is not None and not np.isnan(float(e))
        ]

        if len(valid_primary) == 0:
            return None

        primary_energy = float(valid_primary[0])

        return int(abs(self.E_total - primary_energy) < energy_tolerance_mev)

    def _build_y_usable(self):
        """
        当前第一版：
            可成像 event = 匹配正确且全能量沉积

        后面如果你知道源能量，也可以允许 escape event 用已知 E0 成像。
        """

        if self.y_match is None:
            return None

        if self.y_full is None:
            return self.y_match

        return int(self.y_match == 1 and self.y_full == 1)

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
            "y_full": self.y_full,
            "y_usable": self.y_usable,

            "score": self.score,
            "match_prob": self.match_prob,
            "full_deposition_prob": self.full_deposition_prob,
            "imaging_weight": self.imaging_weight,
        }