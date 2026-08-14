import unittest

import numpy as np

from eiid.domain import EnergyGrid


class EnergyGridTests(unittest.TestCase):
    def test_uniform_first_version_grid_preserves_edges(self):
        grid = EnergyGrid.uniform(0.1, 3.0, 0.1)
        self.assertEqual(grid.bin_count, 29)
        self.assertTrue(np.isclose(grid.edges_mev[0], 0.1))
        self.assertTrue(np.isclose(grid.edges_mev[-1], 3.0))
        self.assertEqual(grid.bin_index(3.0), 28)

    def test_nonuniform_grid_is_supported(self):
        grid = EnergyGrid.nonuniform([0.1, 0.2, 0.5, 1.022, 3.0])
        self.assertEqual(grid.bin_count, 4)
        self.assertEqual(grid.bin_index(1.0), 2)

    def test_width_must_divide_range(self):
        with self.assertRaises(ValueError):
            EnergyGrid.uniform(0.1, 3.0, 0.07)


if __name__ == "__main__":
    unittest.main()

