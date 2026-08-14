from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from validate_stage2_input import validate


class Stage2InputSmokeTests(unittest.TestCase):
    def test_stage2_input_pipeline_closes(self):
        result = validate(
            str(
                PROJECT_ROOT
                / "config"
                / "examples"
                / "experiment_delimited_smoke.json"
            )
        )
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["same_layer_multi_pixel_preserved"])
        self.assertEqual(result["accepted_event_count"], 2)


if __name__ == "__main__":
    unittest.main()
