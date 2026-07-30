import math

import numpy as np


class PlattCalibrator:
    """One-dimensional logistic calibration fitted on unweighted validation."""

    def __init__(self, slope=1.0, intercept=0.0):
        self.slope = float(slope)
        self.intercept = float(intercept)
        self.is_fitted = False

    @staticmethod
    def _sigmoid(value):
        value = float(np.clip(value, -60.0, 60.0))
        return 1.0 / (1.0 + math.exp(-value))

    def fit(
        self,
        logits,
        labels,
        max_iterations=100,
        tolerance=1e-8,
        regularization=1e-6,
    ):
        x = np.asarray(logits, dtype=float)
        y = np.asarray(labels, dtype=float)
        valid = np.isfinite(x) & np.isfinite(y)
        x = x[valid]
        y = y[valid]
        if len(x) == 0 or len(np.unique(y)) < 2:
            self.slope = 1.0
            self.intercept = 0.0
            self.is_fitted = False
            return self

        slope = 1.0
        prior = float(np.clip(np.mean(y), 1e-6, 1.0 - 1e-6))
        intercept = math.log(prior / (1.0 - prior))

        for _ in range(max_iterations):
            linear = np.clip(slope * x + intercept, -60.0, 60.0)
            probabilities = 1.0 / (1.0 + np.exp(-linear))
            residual = probabilities - y
            curvature = probabilities * (1.0 - probabilities)

            gradient = np.array(
                [
                    np.sum(residual * x) + regularization * slope,
                    np.sum(residual) + regularization * intercept,
                ],
                dtype=float,
            )
            hessian = np.array(
                [
                    [
                        np.sum(curvature * x * x) + regularization,
                        np.sum(curvature * x),
                    ],
                    [
                        np.sum(curvature * x),
                        np.sum(curvature) + regularization,
                    ],
                ],
                dtype=float,
            )
            try:
                step = np.linalg.solve(hessian, gradient)
            except np.linalg.LinAlgError:
                break
            step = np.clip(step, -2.0, 2.0)
            slope -= float(step[0])
            intercept -= float(step[1])
            if float(np.linalg.norm(step)) < tolerance:
                break

        self.slope = float(slope)
        self.intercept = float(intercept)
        self.is_fitted = True
        return self

    def transform_logit(self, raw_logit):
        return self.slope * float(raw_logit) + self.intercept

    def predict_probability(self, raw_logit):
        return self._sigmoid(self.transform_logit(raw_logit))

    def to_dict(self):
        return {
            "slope": self.slope,
            "intercept": self.intercept,
            "is_fitted": self.is_fitted,
        }
