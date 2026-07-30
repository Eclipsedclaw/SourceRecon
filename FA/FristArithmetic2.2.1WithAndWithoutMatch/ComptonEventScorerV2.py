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
        energy_feature_mode="full",
        match_calibration=None,
        full_calibration=None,
        matching_probability_threshold=0.5,
    ):
        self.event_list = event_list
        self.energy_scale_mev = energy_scale_mev
        self.distance_scale_mm = distance_scale_mm
        if energy_feature_mode not in ("full", "normalized"):
            raise ValueError(
                "energy_feature_mode 必须是 'full' 或 'normalized'。"
            )
        self.energy_feature_mode = energy_feature_mode
        self.match_calibration = self._prepare_calibration(match_calibration)
        self.full_calibration = self._prepare_calibration(full_calibration)
        self.matching_probability_threshold = float(
            matching_probability_threshold
        )

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
            "energy_fraction_1",
            "energy_fraction_2",
            "energy_fraction_3",

            "distance_12_norm",
            "distance_23_norm",

            "abs_delta_cos_second",
            "delta_cos_second_squared",

            "ends_in_last_layer",
            "starts_in_first_layer",
        ]

        self.match_params = self._prepare_params(
            match_params,
            self._default_match_params(),
        )
        self.full_params = self._prepare_params(
            full_params,
            self._default_full_params(),
        )

    @staticmethod
    def _prepare_calibration(calibration):
        if calibration is None:
            return {"slope": 1.0, "intercept": 0.0}
        return {
            "slope": float(calibration.get("slope", 1.0)),
            "intercept": float(calibration.get("intercept", 0.0)),
        }

    def _calibrated_probability(self, raw_logit, calibration):
        calibrated_logit = (
            calibration["slope"] * raw_logit + calibration["intercept"]
        )
        return self._sigmoid(calibrated_logit), calibrated_logit

    def _prepare_params(self, supplied, defaults):
        params = defaults.copy()
        if supplied is not None:
            for name, value in supplied.items():
                if name in params:
                    params[name] = float(value)
        return params

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
        energy_fractions = [0.0, 0.0, 0.0]
        if E_total > 0:
            for index, value in enumerate(energies[:3]):
                energy_fractions[index] = value / E_total

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
        starts_in_first_layer = 0.0
        if len(layers) > 0:
            ends_in_last_layer = 1.0 if layers[-1] == 2 else 0.0
            starts_in_first_layer = 1.0 if layers[0] == 0 else 0.0

        if self.energy_feature_mode == "normalized":
            E_total_norm = 0.0
            E_mean_norm = 0.0
            E_max_norm = 0.0
        else:
            E_total_norm = E_total / self.energy_scale_mev
            E_mean_norm = E_mean / self.energy_scale_mev
            E_max_norm = E_max / self.energy_scale_mev

        return {
            "bias": 1.0,
            "is_two_hit": is_two_hit,
            "is_three_hit": is_three_hit,
            "is_physical": is_physical,
            "layer_order_score": layer_order_score,

            "E_total_norm": E_total_norm,
            "E_mean_norm": E_mean_norm,
            "E_max_norm": E_max_norm,
            "energy_balance": energy_balance,
            "energy_fraction_1": energy_fractions[0],
            "energy_fraction_2": energy_fractions[1],
            "energy_fraction_3": energy_fractions[2],

            "distance_12_norm": distance_12 / self.distance_scale_mm,
            "distance_23_norm": distance_23 / self.distance_scale_mm,

            "abs_delta_cos_second": abs_delta,
            "delta_cos_second_squared": delta_sq,

            "ends_in_last_layer": ends_in_last_layer,
            "starts_in_first_layer": starts_in_first_layer,
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

        raw_match_prob = self._sigmoid(match_logit)
        raw_full_prob = self._sigmoid(full_logit)
        match_prob, calibrated_match_logit = self._calibrated_probability(
            match_logit,
            self.match_calibration,
        )
        full_prob, calibrated_full_logit = self._calibrated_probability(
            full_logit,
            self.full_calibration,
        )

        event.match_prob_raw = raw_match_prob
        event.full_deposition_prob_raw = raw_full_prob
        event.match_prob = match_prob
        event.full_deposition_prob = full_prob
        event.imaging_weight = match_prob * full_prob
        event.matching_score = match_prob
        threshold = min(
            max(self.matching_probability_threshold, 1e-9),
            1.0 - 1e-9,
        )
        threshold_log_odds = math.log(threshold / (1.0 - threshold))
        event.matching_utility = float(getattr(event, "n_hits", 1)) * (
            calibrated_match_logit - threshold_log_odds
        )

        # ``score`` remains a compatibility alias for event association.
        # Imaging reads ``imaging_weight`` explicitly.
        event.score = event.matching_score

        event.score_features = features
        event.match_logit = match_logit
        event.full_logit = full_logit
        event.calibrated_match_logit = calibrated_match_logit
        event.calibrated_full_logit = calibrated_full_logit

        return event.match_prob, event.full_deposition_prob, event.imaging_weight

    def score_all_events(self):
        for event in self.event_list.events:
            self.score_event(event)
        return self.event_list
