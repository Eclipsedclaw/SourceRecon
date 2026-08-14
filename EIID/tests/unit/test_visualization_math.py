import unittest

import numpy as np

from eiid.coordinates import HealpixSkyGrid
from eiid.visualization import CameraProjection, SphericalMapSmoother


class VisualizationMathTests(unittest.TestCase):
    def test_camera_front_is_at_orthographic_center(self):
        grid = HealpixSkyGrid(4, nested=False)
        front = np.asarray([0.0, 0.0, -1.0])
        front_pixel = grid.direction_to_pixel(front)
        values = np.arange(grid.pixel_count, dtype=float)
        projection = CameraProjection(front, [0.0, 1.0, 0.0])
        raster = projection.front_orthographic_raster(
            grid, values, width=65, height=65
        )
        self.assertEqual(raster[32, 32], values[front_pixel])

    def test_spherical_smoothing_preserves_total_intensity(self):
        grid = HealpixSkyGrid(2, nested=False)
        values = np.zeros(grid.pixel_count)
        values[3] = 2.0
        smoothed = SphericalMapSmoother.smooth(
            values, grid.all_pixel_directions(), np.deg2rad(10.0)
        )
        self.assertAlmostEqual(float(np.sum(smoothed)), 2.0)
        self.assertGreater(np.count_nonzero(smoothed > 0.0), 1)

    def test_numpy_smoothing_memory_limit_is_enforced(self):
        grid = HealpixSkyGrid(2, nested=False)
        with self.assertRaises(MemoryError):
            SphericalMapSmoother.smooth(
                np.ones(grid.pixel_count),
                grid.all_pixel_directions(),
                np.deg2rad(10.0),
                maximum_pixel_count=10,
            )


if __name__ == "__main__":
    unittest.main()
