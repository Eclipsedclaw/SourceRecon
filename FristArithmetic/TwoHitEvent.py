# TwoHitEvent.py

import numpy as np


class TwoHitEvent:
    """
    单个 2-hit 康普顿候选事件。

    一个 TwoHitEvent 对象只表示一个候选 event，例如：
        ch0 -> ch1
        ch0 -> ch2
        ch1 -> ch2

    这个类内部保存：
        1. EventID
        2. 两个 hit 的通道、层号、像素号
        3. 两个 hit 的位置
        4. 两个 hit 的能量
        5. 康普顿角信息
        6. 分数 score
    """

    MEC2_MEV = 0.51099895

    def __init__(self, event_id, hit1, hit2):
        self.event_id = event_id

        self.hit1 = hit1
        self.hit2 = hit2

        self.n_hits = 2
        self.event_type = "2hit"

        self.hit_ids = [hit1["hit_id"], hit2["hit_id"]]
        self.channels = [hit1["channel"], hit2["channel"]]
        self.layers = [hit1["layer"], hit2["layer"]]
        self.pixelids = [hit1["pixelid"], hit2["pixelid"]]

        self.r1 = hit1["pos"]
        self.r2 = hit2["pos"]

        self.E1 = hit1["energy"]
        self.E2 = hit2["energy"]
        self.E_total = self.E1 + self.E2

        self.distance_12 = self._distance(self.r1, self.r2)

        # 2-hit 用第一次散射角生成 Compton cone
        self.cos_theta_c = self._calculate_compton_cos()
        self.theta_c = self._calculate_theta_from_cos(self.cos_theta_c)

        self.is_physical = self._check_physical_validity()

        # 当前先用手写分数，后面可以替换成 ML score
        self.score = self._calculate_score()

    def _distance(self, r_a, r_b):
        return float(np.linalg.norm(r_b - r_a))

    def _calculate_compton_cos(self):
        """
        对 2-hit event，假设：
            第一个 hit 是第一次散射沉积 E1
            第二个 hit 是后续全部沉积 E2

        E_before = E1 + E2
        E_after  = E2
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
        """
        2-hit event 的最基本物理检查：
            cos(theta) 必须在 [-1, 1] 内。
        """

        if np.isnan(self.cos_theta_c):
            return False

        return -1.0 <= self.cos_theta_c <= 1.0

    def _calculate_score(self):
        """
        当前版本的 2-hit 初步分数。

        2-hit 没有内部几何角校验，所以先只根据：
            1. 康普顿角是否合法
            2. layer 顺序是否正常
        给一个简单分数。

        后期这里可以换成：
            score = model.predict(features)
        """

        if not self.is_physical:
            return 0.0

        if self.layers == sorted(self.layers):
            layer_score = 1.0
        else:
            layer_score = 0.2

        return float(layer_score)

    def to_dict(self):
        """
        转成字典，方便后面做 DataFrame 或 debug。
        """

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

            "delta_cos_second": None,
            "is_physical": self.is_physical,
            "score": self.score,
        }