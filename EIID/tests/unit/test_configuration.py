import json
from pathlib import Path
import tempfile
import unittest

from eiid.configuration import ConfigurationError, load_config


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SMOKE_CONFIG = PROJECT_ROOT / "config" / "examples" / "foundation_smoke.json"
STAGE3_CONFIG = PROJECT_ROOT / "config" / "examples" / "stage3_response_smoke.json"
STAGE4_CONFIG = PROJECT_ROOT / "config" / "examples" / "stage4_lmmlem_smoke.json"
STAGE5_CONFIG = PROJECT_ROOT / "config" / "examples" / "stage5_end_to_end_smoke.json"


class ConfigurationTests(unittest.TestCase):
    def test_smoke_configuration_preserves_confirmed_baseline(self):
        config = load_config(str(SMOKE_CONFIG))
        self.assertEqual(config.schema_version, "0.1.0")
        self.assertEqual(config.chamber_to_channel[0], "ch2")
        self.assertEqual(config.trigger.required_channels, ("ch1", "ch2"))
        self.assertEqual(config.energy_grid.minimum_mev, 0.1)
        self.assertEqual(config.energy_grid.maximum_mev, 3.0)
        self.assertEqual(config.paths.project_root, PROJECT_ROOT)

    def test_paths_cannot_escape_project_root(self):
        payload = json.loads(SMOKE_CONFIG.read_text(encoding="utf-8"))
        payload["paths"]["output_root"] = "../../../outside"
        with tempfile.TemporaryDirectory(dir=str(PROJECT_ROOT)) as directory:
            path = Path(directory) / "bad_path.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ConfigurationError):
                load_config(str(path))

    def test_first_version_rejects_changed_energy_range(self):
        payload = json.loads(SMOKE_CONFIG.read_text(encoding="utf-8"))
        payload["energy_grid"]["maximum_mev"] = 2.0
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ConfigurationError):
                load_config(str(path))

    def test_trigger_cannot_add_ch0_as_required_channel(self):
        payload = json.loads(SMOKE_CONFIG.read_text(encoding="utf-8"))
        payload["trigger"]["required_channels"] = ["ch0", "ch1", "ch2"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad_trigger.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ConfigurationError):
                load_config(str(path))

    def test_stage3_response_path_is_typed_and_isolated(self):
        config = load_config(str(STAGE3_CONFIG))
        self.assertIsNotNone(config.response)
        self.assertEqual(config.response.library_status, "prototype_not_formal")
        config.response.library_path.relative_to(config.paths.response_root)

    def test_stage4_reconstruction_parameters_are_typed(self):
        config = load_config(str(STAGE4_CONFIG))
        self.assertIsNotNone(config.reconstruction)
        self.assertEqual(
            config.reconstruction.sensitivity_kind,
            "conditional_acceptance_probability",
        )
        self.assertEqual(config.reconstruction.maximum_iterations, 100)

    def test_stage5_visualization_and_output_names_are_typed(self):
        config = load_config(str(STAGE5_CONFIG))
        self.assertEqual(config.event_response.model_id, "analytic_compton_gaussian_arm_v1")
        self.assertEqual(config.visualization.display_up_direction, (0.0, 1.0, 0.0))
        self.assertEqual(
            config.output.file_names["event_summary"], "event_summary.csv"
        )


if __name__ == "__main__":
    unittest.main()
