import unittest

import numpy as np

from eiid.response import SparseEventResponse


class SparseEventResponseTests(unittest.TestCase):
    def test_duplicate_cells_are_sorted_and_coalesced(self):
        response = SparseEventResponse(
            event_id="e1",
            cell_count=5,
            cell_indices=np.asarray([2, 1, 2]),
            values=np.asarray([0.2, 0.3, 0.4]),
            model_id="test",
        )
        self.assertTrue(np.array_equal(response.cell_indices, [1, 2]))
        self.assertTrue(np.allclose(response.values, [0.3, 0.6]))
        self.assertAlmostEqual(response.dot(np.ones(5)), 0.9)

    def test_empty_response_retains_reason(self):
        response = SparseEventResponse.empty("back", 4, "test", "unsupported")
        self.assertEqual(response.nonzero_count, 0)
        self.assertEqual(response.diagnostics["empty_reason"], "unsupported")


if __name__ == "__main__":
    unittest.main()

