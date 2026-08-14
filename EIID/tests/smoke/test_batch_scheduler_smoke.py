import json
from pathlib import Path
import sys
import tempfile
import unittest

from eiid.batch import MemoryAwareBatchScheduler


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class BatchSchedulerSmokeTests(unittest.TestCase):
    def test_one_dataset_subprocess_manifest_and_success_close(self):
        source = json.loads(
            (PROJECT_ROOT / "config/examples/stage5_end_to_end_smoke.json").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory(dir=str(PROJECT_ROOT)) as directory:
            root = Path(directory)
            source["profile_purpose"] = "batch_scheduler_smoke"
            source["paths"] = {
                "project_root": str(PROJECT_ROOT),
                "input_root": str(PROJECT_ROOT / "data/input"),
                "response_root": str(PROJECT_ROOT / "response_campaign/response_library"),
                "output_root": str(root / "runs"),
                "log_root": str(root / "logs"),
            }
            source["input"]["dataset_id"] = "batch_scheduler_smoke_unique"
            source["input"]["paths"] = {
                channel: str(PROJECT_ROOT / "tests/fixtures/experiment" / (channel + ".tsv"))
                for channel in ("ch0", "ch1", "ch2")
            }
            source["visualization"]["enabled"] = False
            source["reconstruction"].update({
                "maximum_iterations": 2,
                "minimum_iterations": 0,
                "likelihood_relative_tolerance": None,
                "image_relative_tolerance": None,
            })
            config_path = root / "dataset.json"
            config_path.write_text(json.dumps(source), encoding="utf-8")
            batch = {
                "schema_version": "eiid.batch.v1",
                "project_root": str(PROJECT_ROOT),
                "maximum_workers": 1,
                "skip_completed": True,
                "batch_output_root": str(root / "batch_runs"),
                "memory_guard": {
                    "enabled": True,
                    "minimum_available_gib": 0.001,
                    "estimated_worker_peak_gib": 0.001,
                    "poll_interval_seconds": 0.05,
                    "maximum_retries": 0,
                    "termination_grace_seconds": 2.0,
                },
                "datasets": [{
                    "dataset_id": "batch_scheduler_smoke_unique",
                    "config": str(config_path),
                }],
            }
            manifest_path = root / "batch.json"
            manifest_path.write_text(json.dumps(batch), encoding="utf-8")
            result = MemoryAwareBatchScheduler(
                manifest_path, python_executable=sys.executable
            ).run()
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["datasets"][0]["status"], "success")
            batch_directory = Path(result["batch_directory"])
            self.assertTrue((batch_directory / "SUCCESS.json").is_file())
            self.assertTrue((batch_directory / "memory_telemetry.csv").is_file())


if __name__ == "__main__":
    unittest.main()
