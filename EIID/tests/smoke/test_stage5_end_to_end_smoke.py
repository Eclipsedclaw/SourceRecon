import json
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from eiid.application import run_experiment


class Stage5EndToEndSmokeTests(unittest.TestCase):
    def test_experiment_to_joint_image_and_figures_closes(self):
        result = run_experiment(
            str(
                PROJECT_ROOT
                / "config"
                / "examples"
                / "stage5_end_to_end_smoke.json"
            ),
            run_kind="stage5_smoke",
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["accepted_event_count"], 2)
        self.assertEqual(result["supported_event_count"], 2)
        self.assertFalse(result["physical_use_allowed"])
        self.assertEqual(len(result["figure_outputs"]), 13)
        for path in result["figure_outputs"].values():
            figure = Path(path)
            self.assertTrue(figure.is_file())
            self.assertGreater(figure.stat().st_size, 1000)
        run_directory = PROJECT_ROOT / "runs" / result["run_id"]
        self.assertTrue((run_directory / "SUCCESS.json").is_file())
        summary = json.loads(
            (run_directory / "reconstruction_summary.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(summary["run_id"], result["run_id"])
        with self.assertRaises(ValueError):
            run_experiment(
                str(
                    PROJECT_ROOT
                    / "config"
                    / "examples"
                    / "stage5_end_to_end_smoke.json"
                ),
                run_kind="stage5_resume_guard",
                resume_from_run_id=result["run_id"],
            )


if __name__ == "__main__":
    unittest.main()
