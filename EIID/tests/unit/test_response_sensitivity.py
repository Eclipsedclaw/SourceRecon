import unittest

import numpy as np

from eiid.response import (
    SensitivityBundle,
    SensitivityEstimator,
    SensitivityKind,
    SensitivityMap,
)


class ResponseSensitivityTests(unittest.TestCase):
    def setUp(self):
        self.conditional = SensitivityEstimator.conditional_acceptance(
            accepted_count=np.full((2, 3), 100.0),
            generated_count=np.full((2, 3), 1000.0),
            definition="digitized ch1 AND ch2 accepted",
        )

    def test_three_physical_definitions_are_not_mixed(self):
        area = SensitivityEstimator.effective_area(self.conditional, 200.0)
        emitted = SensitivityEstimator.finite_distance_emitted_probability(
            self.conditional, np.pi, 2000.0
        )
        bundle = SensitivityBundle(self.conditional, area, emitted)
        self.assertTrue(np.allclose(self.conditional.values, 0.1))
        self.assertTrue(np.allclose(area.values, 20.0))
        self.assertTrue(np.allclose(emitted.values, 0.025))
        self.assertEqual(area.unit, "cm2")
        self.assertIs(
            bundle.by_kind(SensitivityKind.FINITE_DISTANCE_EMITTED_PROBABILITY),
            emitted,
        )

    def test_probability_cannot_use_effective_area_values(self):
        with self.assertRaises(ValueError):
            SensitivityMap(
                kind=SensitivityKind.CONDITIONAL_ACCEPTANCE_PROBABILITY,
                values=np.full((1, 1), 20.0),
                standard_error=np.zeros((1, 1)),
                unit="1",
                definition="invalid",
            )

    def test_invalid_monte_carlo_denominator_is_rejected(self):
        with self.assertRaises(ValueError):
            SensitivityEstimator.conditional_acceptance(
                np.ones((1, 1)),
                np.zeros((1, 1)),
                definition="invalid zero denominator",
            )


if __name__ == "__main__":
    unittest.main()
