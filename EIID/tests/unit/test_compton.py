import unittest

import numpy as np

from eiid.physics import ComptonKinematics


class ComptonTests(unittest.TestCase):
    def test_impossible_incident_energy_is_rejected(self):
        self.assertIsNone(ComptonKinematics.scatter_angle_rad(0.1, 0.2))

    def test_candidate_scatter_angle_is_physical(self):
        angle = ComptonKinematics.scatter_angle_rad(0.662, 0.15)
        self.assertIsNotNone(angle)
        self.assertGreaterEqual(angle, 0.0)
        self.assertLessEqual(angle, np.pi)

    def test_normal_forward_positions_give_negative_z_source_axis(self):
        axis = ComptonKinematics.source_side_axis(
            [0.0, 0.0, -30.0], [0.0, 0.0, 0.0]
        )
        self.assertTrue(np.allclose(axis, [0.0, 0.0, -1.0]))


if __name__ == "__main__":
    unittest.main()

