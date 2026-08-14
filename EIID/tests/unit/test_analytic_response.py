import unittest

import numpy as np

from eiid.domain import (
    Channel,
    DigitizedHit,
    EnergyGrid,
    MeasuredEvent,
    SequenceClass,
)
from eiid.physics import ComptonKinematics
from eiid.response import AnalyticComptonResponse


def make_event(sequence=SequenceClass.NORMAL_FORWARD):
    return MeasuredEvent(
        event_id="analytic",
        sequence_class=sequence,
        hits=(
            DigitizedHit(
                hit_id="ch2",
                channel=Channel.CH2,
                layer=0,
                pixel_id="2",
                position_mm=np.asarray([0.0, 0.0, -30.0]),
                energy_mev=0.1,
            ),
            DigitizedHit(
                hit_id="ch1",
                channel=Channel.CH1,
                layer=1,
                pixel_id="1",
                position_mm=np.asarray([0.0, 0.0, 0.0]),
                energy_mev=0.2,
            ),
        ),
    )


class AnalyticResponseTests(unittest.TestCase):
    def test_unknown_incident_energy_keeps_multiple_candidates(self):
        grid = EnergyGrid.nonuniform([0.3, 0.4, 0.6, 0.7])
        directions = []
        for energy in (0.35, 0.65):
            angle = ComptonKinematics.scatter_angle_rad(energy, 0.1)
            directions.append([np.sin(angle), 0.0, -np.cos(angle)])
        model = AnalyticComptonResponse(
            arm_sigma_rad=np.deg2rad(1.0),
            minimum_relative_weight=1e-6,
        )
        response = model.evaluate(make_event(), np.asarray(directions), grid)
        supported_energy = np.unique(response.cell_indices % grid.bin_count)
        self.assertGreaterEqual(supported_energy.size, 2)
        self.assertEqual(
            response.diagnostics["response_semantics"],
            "prototype_relative_likelihood_not_normalized",
        )

    def test_backscatter_is_retained_but_normal_component_is_empty(self):
        grid = EnergyGrid.nonuniform([0.3, 0.4])
        model = AnalyticComptonResponse(np.deg2rad(2.0))
        response = model.evaluate(
            make_event(SequenceClass.BACKSCATTER),
            np.asarray([[0.0, 0.0, -1.0]]),
            grid,
        )
        self.assertEqual(response.nonzero_count, 0)
        self.assertEqual(
            response.diagnostics["empty_reason"],
            "backscatter_component_not_enabled",
        )


if __name__ == "__main__":
    unittest.main()
