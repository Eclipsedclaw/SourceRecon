import unittest

import numpy as np

from eiid.coordinates import HealpixSkyGrid, RingHealpixMath


class RingHealpixMathTests(unittest.TestCase):
    def test_nside_one_known_centers(self):
        directions = RingHealpixMath(1).pixels_to_directions(np.arange(12))
        self.assertTrue(np.allclose(directions[4], [1.0, 0.0, 0.0]))
        self.assertTrue(np.allclose(directions[5], [0.0, 1.0, 0.0]))
        self.assertAlmostEqual(directions[0, 2], 2.0 / 3.0)
        self.assertAlmostEqual(directions[8, 2], -2.0 / 3.0)

    def test_all_pixel_centers_roundtrip_without_healpy(self):
        for nside in (1, 2, 4, 8):
            grid = RingHealpixMath(nside)
            pixels = np.arange(grid.pixel_count)
            recovered = grid.directions_to_pixels(
                grid.pixels_to_directions(pixels)
            )
            self.assertTrue(np.array_equal(recovered, pixels))

    def test_healpix_wrapper_exposes_vectorized_ring_fallback(self):
        grid = HealpixSkyGrid(4, nested=False)
        directions = grid.all_pixel_directions()
        self.assertEqual(directions.shape, (grid.pixel_count, 3))
        self.assertTrue(
            np.array_equal(
                grid.directions_to_pixels(directions),
                np.arange(grid.pixel_count),
            )
        )


if __name__ == "__main__":
    unittest.main()

