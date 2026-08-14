import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from eiid.application import run_experiment
from eiid.domain import EnergyGrid
from eiid.response import (
    PortableNpzJsonResponseStore,
    ResponseCampaignBuilder,
    ResponseLibraryMetadata,
    ResponseNodeTable,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class HybridEndToEndSmokeTests(unittest.TestCase):
    def test_candidate_library_is_used_but_not_marked_physical(self):
        with tempfile.TemporaryDirectory(dir=str(PROJECT_ROOT)) as directory:
            root = Path(directory)
            nside = 4
            sky_count = 12 * nside * nside
            energy_grid = EnergyGrid.uniform(0.1, 3.0, 0.1)
            sky, energy = np.indices((sky_count, energy_grid.bin_count))
            size = sky_count * energy_grid.bin_count
            table = ResponseNodeTable(
                sky.reshape(-1), energy.reshape(-1),
                np.full(size, 1000.0), np.full(size, 100.0),
                np.full(size, 8.0), {},
            )
            metadata = ResponseLibraryMetadata(
                library_id="hybrid_smoke_candidate",
                schema_version="1.0.0",
                library_status="candidate_unvalidated",
                response_model_kind="hybrid_monte_carlo_arm_v1",
                geometry_version="synthetic-smoke",
                physics_list="synthetic-smoke",
                digitizer_version="truth-smoke",
                trigger_definition="valid_hit(ch1) AND valid_hit(ch2)",
            )
            library = ResponseCampaignBuilder().build(
                table, energy_grid,
                {"type": "healpix", "nside": nside, "nested": False, "pixel_count": sky_count},
                metadata,
                {
                    "source_mode": "far_field_parallel_beam",
                    "generation_area_cm2": 100.0,
                    "generated_count_included_zero_deposit_events": True,
                },
            )
            response_root = root / "response"
            library_path = response_root / "hybrid_smoke_candidate"
            PortableNpzJsonResponseStore().save(library, library_path)

            config = json.loads(
                (PROJECT_ROOT / "config/examples/stage5_end_to_end_smoke.json").read_text(encoding="utf-8")
            )
            config["profile_purpose"] = "hybrid_end_to_end_smoke"
            config["paths"] = {
                "project_root": str(PROJECT_ROOT),
                "input_root": str(PROJECT_ROOT / "data/input"),
                "response_root": str(response_root),
                "output_root": str(root / "runs"),
                "log_root": str(root / "logs"),
            }
            config["input"]["dataset_id"] = "hybrid_end_to_end_smoke"
            config["input"]["paths"] = {
                channel: str(PROJECT_ROOT / "tests/fixtures/experiment" / (channel + ".tsv"))
                for channel in ("ch0", "ch1", "ch2")
            }
            config["response"] = {
                "adapter": "portable_npz_json_v1",
                "library_path": str(library_path),
                "library_status": "candidate_unvalidated",
                "overwrite_existing": False,
                "parameters": {},
            }
            config["event_response"] = {
                "model_id": "hybrid_monte_carlo_arm_v1",
                "parameters": {"minimum_relative_weight": 1e-8, "allow_unvalidated_response": True},
            }
            config["reconstruction"].update({
                "maximum_iterations": 2,
                "minimum_iterations": 0,
                "likelihood_relative_tolerance": None,
                "image_relative_tolerance": None,
            })
            config["visualization"]["enabled"] = False
            config_path = root / "hybrid.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            result = run_experiment(str(config_path), run_kind="hybrid_smoke")
            self.assertEqual(result["status"], "ok")
            self.assertFalse(result["physical_use_allowed"])
            self.assertEqual(result["response_provenance"]["library_id"], "hybrid_smoke_candidate")
            self.assertEqual(result["response_semantics"], "hybrid_calibrated_event_density")


if __name__ == "__main__":
    unittest.main()
