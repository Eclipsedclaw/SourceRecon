from pathlib import Path
import tempfile
import unittest

import numpy as np

from eiid.domain import EnergyGrid
from eiid.response import (
    PrototypeNpzJsonResponseStore,
    ResponseLibrary,
    ResponseLibraryMetadata,
    SensitivityBundle,
    SensitivityEstimator,
)


class ResponseStorageTests(unittest.TestCase):
    def _library(self):
        conditional = SensitivityEstimator.conditional_acceptance(
            np.full((2, 2), 10.0),
            np.full((2, 2), 100.0),
            definition="test acceptance",
        )
        return ResponseLibrary(
            metadata=ResponseLibraryMetadata(
                library_id="unit",
                schema_version="0.1.0",
                library_status="prototype_not_formal",
                response_model_kind="unit",
                geometry_version="synthetic",
                physics_list="synthetic",
                digitizer_version="truth",
                trigger_definition="ch1 AND ch2",
            ),
            energy_grid=EnergyGrid.nonuniform([0.1, 0.2, 0.3]),
            sky_grid={"type": "test", "pixel_count": 2},
            sensitivities=SensitivityBundle(conditional),
            calibration_arrays={"arm_sigma_rad": np.full((2, 2), 0.1)},
        )

    def test_prototype_store_roundtrip_and_completion_hash(self):
        store = PrototypeNpzJsonResponseStore()
        with tempfile.TemporaryDirectory() as directory:
            store.save(self._library(), directory)
            self.assertTrue(store.is_complete(directory))
            loaded = store.load(directory)
            self.assertEqual(loaded.metadata.library_id, "unit")
            self.assertTrue(
                np.allclose(loaded.sensitivities.conditional.values, 0.1)
            )
            self.assertTrue(
                np.allclose(loaded.calibration_arrays["arm_sigma_rad"], 0.1)
            )
            (Path(directory) / store.COMPLETION_NAME).unlink()
            self.assertFalse(store.is_complete(directory))
            with self.assertRaises(ValueError):
                store.load(directory)

    def test_overwrite_requires_explicit_permission(self):
        store = PrototypeNpzJsonResponseStore()
        with tempfile.TemporaryDirectory() as directory:
            store.save(self._library(), directory)
            with self.assertRaises(FileExistsError):
                store.save(self._library(), directory)


if __name__ == "__main__":
    unittest.main()
