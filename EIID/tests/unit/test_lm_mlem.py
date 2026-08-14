import unittest

import numpy as np

from eiid.reconstruction import LmMlemConfig, ListModeMlemSolver
from eiid.response import (
    SensitivityKind,
    SensitivityMap,
    SparseEventResponse,
)


def response(event_id, values):
    selected = np.flatnonzero(np.asarray(values) > 0.0)
    return SparseEventResponse(
        event_id=event_id,
        cell_count=2,
        cell_indices=selected,
        values=np.asarray(values, dtype=float)[selected],
        model_id="unit_matrix",
    )


def sensitivity():
    return SensitivityMap(
        kind=SensitivityKind.CONDITIONAL_ACCEPTANCE_PROBABILITY,
        values=np.asarray([[1.0, 1.0]]),
        standard_error=np.zeros((1, 2)),
        unit="1",
        definition="two discrete accepted categories",
    )


class LmMlemTests(unittest.TestCase):
    def solver(self):
        return ListModeMlemSolver(
            LmMlemConfig(
                maximum_iterations=100,
                minimum_iterations=3,
                denominator_floor=1e-12,
                sensitivity_floor=1e-12,
                likelihood_relative_tolerance=1e-10,
                image_relative_tolerance=1e-8,
                convergence_patience=3,
            )
        )

    def test_small_matrix_likelihood_is_monotonic_and_main_cell_is_recovered(self):
        events = []
        events.extend(response("a{}".format(i), [0.8, 0.1]) for i in range(20))
        events.extend(response("b{}".format(i), [0.2, 0.9]) for i in range(8))
        result = self.solver().run(events, sensitivity())
        likelihood = [item.log_likelihood for item in result.telemetry]
        self.assertTrue(np.all(np.diff(likelihood) >= -1e-9))
        self.assertGreater(result.image[0], result.image[1])
        self.assertGreater(result.completed_iterations, 0)

    def test_empty_dataset_is_rejected(self):
        with self.assertRaises(ValueError):
            self.solver().run([], sensitivity())

    def test_zero_response_without_background_cannot_create_intensity(self):
        empty = SparseEventResponse.empty("empty", 2, "unit", "no_kernel")
        with self.assertRaises(FloatingPointError):
            self.solver().run([empty], sensitivity())

    def test_sensitivity_zero_cell_is_kept_at_zero(self):
        map_with_zero = SensitivityMap(
            kind=SensitivityKind.CONDITIONAL_ACCEPTANCE_PROBABILITY,
            values=np.asarray([[1.0, 0.0]]),
            standard_error=np.zeros((1, 2)),
            unit="1",
            definition="second cell unsupported",
        )
        events = [response("only", [1.0, 0.0])]
        result = self.solver().run(events, map_with_zero)
        self.assertEqual(result.image[1], 0.0)


if __name__ == "__main__":
    unittest.main()

