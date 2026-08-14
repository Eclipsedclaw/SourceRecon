import json
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from validate_stage4_lmmlem import validate


class Stage4LmMlemSmokeTests(unittest.TestCase):
    def test_run_identity_reconstruction_telemetry_and_success_marker_close(self):
        result = validate(
            str(
                PROJECT_ROOT
                / "config"
                / "examples"
                / "stage4_lmmlem_smoke.json"
            )
        )
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["likelihood_monotonic"])
        self.assertFalse(result["formal_physical_response_used"])
        run_directory = Path(result["run_directory"])
        self.assertTrue((run_directory / "SUCCESS.json").is_file())
        manifest = json.loads(
            (run_directory / "run_manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["run_id"], result["run_id"])
        self.assertEqual(manifest["status"], "success")
        metric_lines = (
            run_directory / "numerical" / "iteration_metrics.jsonl"
        ).read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(metric_lines), result["iteration_metric_count"])


if __name__ == "__main__":
    unittest.main()
