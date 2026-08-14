from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from validate_foundation import validate


class FoundationSmokeTests(unittest.TestCase):
    def test_foundation_validation_closes(self):
        result = validate(
            str(PROJECT_ROOT / "config" / "examples" / "foundation_smoke.json")
        )
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["trigger"]["accepted"])
        self.assertEqual(result["sky_grid"]["pixel_count"], 768)


if __name__ == "__main__":
    unittest.main()
