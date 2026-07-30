# ComptonEventScorerV2.py

import math
import numpy as np


class ComptonEventScorerV2:
    """
    双头打分器：

        match_prob:
            candidate hit 是否来自同一条 gamma

        full_deposition_prob:
            是否全能量沉积

        imaging_weight:
            用于成像的最终权重
    """

    def __init__(
        self,
        event_list,
        match_params=None,
        full_params=None,
        energy_scale_mev=1.0,
        distance_scale_mm=100.0,
    ):
        self.event_list = event_list
        self.energy_scale_mev = energy_scale_mev
        self.distance_scale_mm = distance_scale_mm

        self.feature_names = [
            "bias",
            "is_two_hit",
            "is_three_hit",
            "is_physical",
            "layer_order_score",

            "E_total_norm",
            "E_mean_norm",
            "E_max_norm",
            "energy_balance",

            "distance_12_norm",
            "distance_23_norm",

            "abs_delta_cos_second",
            "delta_cos_second_squared",

            "ends_in_last_layer",
        ]

        self.match_params = match_params or self._default_match_params()
        self.full_params = full_params or self._default_full_params()

    def _default_match_params(self):
        params = {name: 0.0 for name in self.feature_names}

        params.update(
            {
                "bias": -1.0,
                "is_two_hit": -0.1,
                "is_three_hit": 0.2,
                "is_physical": 0.5,
                "layer_order_score": 0.5,
                "abs_delta_cos_second": -0.5,
                "delta_cos_second_squared": -0.3,
            }
        )

        return params

    def _default_full_params(self):
        params = {name: 0.0 for name in self.feature_names}

        params.update(
            {
                "bias": -1.0,
                "is_two_hit": -0.8,
                "is_three_hit": 0.5,
                "is_physical": 0.5,
                "energy_balance": 0.3,
                "abs_delta_cos_second": -2.5,
                "delta_cos_second_squared": -1.5,
                "ends_in_last_layer": 0.5,
            }
        )

        return params

    def _sigmoid(self, x):
        if x >= 0:
            return 1.0 / (1.0 + math.exp(-x))
        exp_x = math.exp(x)
        return exp_x / (1.0 + exp_x)

    def _safe(self, value, default=0.0):
        if value is None:
            return default
        try:
            if np.isnan(value):
                return default
        except TypeError:
            pass
        return float(value)

    def extract_features(self, event):
        n_hits = getattr(event, "n_hits", 0)

        is_two_hit = 1.0 if n_hits == 2 else 0.0
        is_three_hit = 1.0 if n_hits == 3 else 0.0
        is_physical = 1.0 if getattr(event, "is_physical", False) else 0.0

        layers = getattr(event, "layers", [])
        if len(layers) > 0 and layers == sorted(layers):
            layer_order_score = 1.0
        else:
            layer_order_score = 0.2

        energies = []
        for name in ["E1", "E2", "E3"]:
            if hasattr(event, name):
                value = getattr(event, name)
                if value is not None:
                    energies.append(self._safe(value))

        E_total = sum(energies)
        E_mean = float(np.mean(energies)) if len(energies) else 0.0
        E_max = max(energies) if len(energies) else 0.0
        E_min = min(energies) if len(energies) else 0.0

        energy_balance = E_min / E_max if E_max > 0 else 0.0

        distance_12 = self._safe(getattr(event, "distance_12", 0.0))
        distance_23 = self._safe(getattr(event, "distance_23", 0.0))

        if n_hits == 3:
            delta = self._safe(getattr(event, "delta_cos_second", 0.0))
            abs_delta = abs(delta)
            delta_sq = delta ** 2
        else:
            abs_delta = 0.0
            delta_sq = 0.0

        ends_in_last_layer = 0.0
        if len(layers) > 0:
            ends_in_last_layer = 1.0 if layers[-1] == max(layers) else 0.0

        return {
            "bias": 1.0,
            "is_two_hit": is_two_hit,
            "is_three_hit": is_three_hit,
            "is_physical": is_physical,
            "layer_order_score": layer_order_score,

            "E_total_norm": E_total / self.energy_scale_mev,
            "E_mean_norm": E_mean / self.energy_scale_mev,
            "E_max_norm": E_max / self.energy_scale_mev,
            "energy_balance": energy_balance,

            "distance_12_norm": distance_12 / self.distance_scale_mm,
            "distance_23_norm": distance_23 / self.distance_scale_mm,

            "abs_delta_cos_second": abs_delta,
            "delta_cos_second_squared": delta_sq,

            "ends_in_last_layer": ends_in_last_layer,
        }

    def _logit(self, features, params):
        value = 0.0
        for name in self.feature_names:
            value += params[name] * features[name]
        return value

    def score_event(self, event):
        features = self.extract_features(event)

        match_logit = self._logit(features, self.match_params)
        full_logit = self._logit(features, self.full_params)

        match_prob = self._sigmoid(match_logit)
        full_prob = self._sigmoid(full_logit)

        event.match_prob = match_prob
        event.full_deposition_prob = full_prob
        event.imaging_weight = match_prob * full_prob

        # 兼容 EventMatcher
        event.score = event.imaging_weight

        event.score_features = features
        event.match_logit = match_logit
        event.full_logit = full_logit

        return event.match_prob, event.full_deposition_prob, event.imaging_weight

    def score_all_events(self):
        for event in self.event_list.events:
            self.score_event(event)
        return self.event_list