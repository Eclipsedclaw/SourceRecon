from pathlib import Path
import tempfile
import unittest

import numpy as np

from eiid.convergence import IterationRecorder


class CheckpointRecoveryTests(unittest.TestCase):
    def test_latest_complete_checkpoint_is_loaded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recorder = IterationRecorder(
                root / "numerical",
                root / "checkpoints",
                sky_pixel_count=2,
                energy_bin_count=2,
            )
            recorder._save_snapshot(2, np.arange(4, dtype=float))
            recorder._save_snapshot(5, np.arange(4, dtype=float) + 1.0)
            iteration, image, path = IterationRecorder.load_latest_checkpoint(
                root / "checkpoints"
            )
            self.assertEqual(iteration, 5)
            self.assertEqual(path.name, "iteration_000005.npz")
            self.assertTrue(
                np.array_equal(image, (np.arange(4) + 1.0).reshape(2, 2))
            )

    def test_missing_checkpoint_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                IterationRecorder.load_latest_checkpoint(directory)


if __name__ == "__main__":
    unittest.main()
