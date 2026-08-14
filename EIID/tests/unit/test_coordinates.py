import unittest

import numpy as np

from eiid.coordinates import CoordinateConvention, HealpixSkyGrid


class CoordinateTests(unittest.TestCase):
    def setUp(self):
        self.convention = CoordinateConvention([0, 0, 1], [0, 0, -1])

    def test_geant4_forward_propagation_points_to_negative_z_source(self):
        source = self.convention.propagation_to_source([0, 0, 1])
        self.assertTrue(np.allclose(source, [0, 0, -1]))
        self.assertTrue(self.convention.is_camera_front(source))

    def test_opposite_coordinate_pair_is_required(self):
        with self.assertRaises(ValueError):
            CoordinateConvention([0, 0, 1], [1, 0, 0])

    def test_healpix_pixel_count_does_not_require_healpy(self):
        self.assertEqual(HealpixSkyGrid(8).pixel_count, 768)

    def test_healpix_nside_must_be_power_of_two(self):
        with self.assertRaises(ValueError):
            HealpixSkyGrid(3)


if __name__ == "__main__":
    unittest.main()

