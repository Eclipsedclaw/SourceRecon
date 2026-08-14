import json
from pathlib import Path
import tempfile
import unittest

from eiid.batch import BatchManifestLoader


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class BatchManifestTests(unittest.TestCase):
    def test_dataset_identity_and_project_isolation_are_validated(self):
        payload = {
            "schema_version": "eiid.batch.v1",
            "project_root": str(PROJECT_ROOT),
            "maximum_workers": 2,
            "memory_guard": {
                "enabled": True,
                "minimum_available_gib": 1.0,
                "estimated_worker_peak_gib": 0.5,
            },
            "datasets": [
                {
                    "dataset_id": "stage5_smoke",
                    "config": "config/examples/stage5_end_to_end_smoke.json",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "batch.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            _, root, _, jobs = BatchManifestLoader.load(path)
        self.assertEqual(root, PROJECT_ROOT)
        self.assertEqual(jobs[0].dataset_id, "stage5_smoke")


if __name__ == "__main__":
    unittest.main()
