# TwoHitEvent.py

import numpy as np


class TwoHitEvent:
    """
    单个 2-hit 康普顿候选事件。

    重要说明（天基约束）：
        2-hit 事件没有内部冗余约束，无法像 3-hit 那样自证清白。
        它的锥角公式假设 E1 + E2 = 真实入射能量（全吸收），
        这个假设在未知能谱下无法验证。

        因此当前物理管线中 2-hit 默认不参与成像
        （见 ComptonConeImager 的 include_two_hit 参数），
        等有宽谱 Geant4 MC 后，
        用"全吸收概率分类器"作为门控再启用。

        本类只做小改动：
            新增能量份额等能量尺度无关的特征属性，
            供未来的 MC 分类器使用。
    """

    MEC2_MEV = 0.51099895

    def __init__(self, event_id, hit1, hit2, resolution_model=None):
        self.event_id = event_id

        self.hit1 = hit1
        self.hit2 = hit2

        self.n_hits = 2
        self.event_type = "2hit"

        self.resolution_model = resolution_model

        self.hit_ids = [hit1["hit_id"], hit2["hit_id"]]
        self.channels = [hit1["channel"], hit2["channel"]]
        self.layers = [hit1["layer"], hit2["layer"]]
        self.pixelids = [hit1["pixelid"], hit2["pixelid"]]

        self.r1 = hit1["pos"]
        self.r2 = hit2["pos"]

        self.E1 = hit1["energy"]
        self.E2 = hit2["energy"]
        self.E_total = self.E1 + self.E2

        # ===== 新增：能量尺度无关的特征（供未来 MC 分类器使用）=====
        if self.E_total > 0:
            self.E1_fraction = self.E1 / self.E_total
        else:
            self.E1_fraction = 0.0

        # 事件终止在哪一层：
        # 终止层越深，全吸收的先验概率通常越高
        self.stop_layer = max(self.layers) if len(self.layers) > 0 else -1

        self.distance_12 = self._distance(self.r1, self.r2)

        # 2-hit 锥角：注意它仅在全吸收假设成立时正确
        self.cos_theta_c = self._calculate_compton_cos()
        self.theta_c = self._calculate_theta_from_cos(self.cos_theta_c)

        self.is_physical = self._check_physical_validity()

        self.score = self._calculate_score()

    def _distance(self, r_a, r_b):
        return float(np.linalg.norm(r_b - r_a))

    def _calculate_compton_cos(self):
        """
        E_before = E1 + E2
        E_after  = E2

        再次强调：这个公式隐含"全吸收"假设。
        """

        if self.E_total <= 0 or self.E2 <= 0:
            return np.nan

        cos_theta = 1.0 - self.MEC2_MEV * (
            1.0 / self.E2 - 1.0 / self.E_total
        )

        return float(cos_theta)

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

    def _calculate_score(self):
        """
        2-hit 无法自检，只能给一个基础分。

        真正的门控（全吸收概率）要等 MC 训练的分类器。
        """

        if not self.is_physical:
            return 0.0

        if self.layers == sorted(self.layers):
            layer_score = 1.0
        else:
            layer_score = 0.2

        return float(layer_score)

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
            "E1_fraction": self.E1_fraction,
            "stop_layer": self.stop_layer,

            "r1": self.r1,
            "r2": self.r2,
            "r3": None,

            "distance_12": self.distance_12,
            "distance_23": None,

            "cos_theta_c": self.cos_theta_c,
            "theta_c": self.theta_c,

            "delta_cos_second": None,
            "sigma_delta_second": None,
            "pull_second": None,

            "is_physical": self.is_physical,
            "score": self.score,
        }