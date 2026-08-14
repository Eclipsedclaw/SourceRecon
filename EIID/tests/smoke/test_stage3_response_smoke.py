from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from validate_stage3_response import validate


class Stage3ResponseSmokeTests(unittest.TestCase):
    def test_response_and_sensitivity_roundtrip_closes(self):
        result = validate(
            str(
                PROJECT_ROOT
                / "config"
                / "examples"
                / "stage3_response_smoke.json"
            )
        )
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["formal_response_format_decided"])
        self.assertIn(result["run_id"], result["response_library_directory"])
        self.assertTrue(
            (
                Path(result["response_library_directory"]) / "SUCCESS.json"
            ).is_file()
        )
        self.assertGreaterEqual(result["analytic_supported_energy_bin_count"], 2)
        self.assertAlmostEqual(
            result["finite_distance_s_emitted"],
            result["conditional_acceptance_probability"]
            * result["solid_angle_fraction_of_4pi"],
        )


if __name__ == "__main__":
    unittest.main()
