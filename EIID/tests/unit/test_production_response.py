from pathlib import Path
import tempfile
import unittest

import numpy as np

from eiid.domain import Channel, DigitizedHit, EnergyGrid, MeasuredEvent
from eiid.response import (
    HybridMonteCarloResponse,
    PortableNpzJsonResponseStore,
    ResponseCampaignBuilder,
    ResponseLibraryMetadata,
    ResponseNodeTable,
)


class ProductionResponseTests(unittest.TestCase):
    def test_validated_status_requires_independent_validation_evidence(self):
        with self.assertRaises(ValueError):
            ResponseLibraryMetadata(
                library_id="invalid-claim", schema_version="1.0.0",
                library_status="validated_physical",
                response_model_kind="hybrid_monte_carlo_arm_v1",
                geometry_version="g", physics_list="p", digitizer_version="d",
                trigger_definition="valid_hit(ch1) AND valid_hit(ch2)",
            )

    def _library(self):
        sky_count = 12
        energy_count = 2
        sky, energy = np.indices((sky_count, energy_count))
        table = ResponseNodeTable(
            sky_pixel_index=sky.reshape(-1),
            energy_bin_index=energy.reshape(-1),
            generated_count=np.full(sky_count * energy_count, 1000.0),
            accepted_count=np.full(sky_count * energy_count, 100.0),
            arm_sigma_deg=np.full(sky_count * energy_count, 6.0),
            topology_counts={
                "normal_forward": np.full(sky_count * energy_count, 80.0),
                "backscatter": np.full(sky_count * energy_count, 20.0),
            },
        )
        return ResponseCampaignBuilder().build(
            table,
            EnergyGrid.nonuniform([0.1, 1.0, 3.0]),
            {"type": "healpix", "nside": 1, "nested": False, "pixel_count": 12},
            ResponseLibraryMetadata(
                library_id="candidate",
                schema_version="1.0.0",
                library_status="candidate_unvalidated",
                response_model_kind="hybrid_monte_carlo_arm_v1",
                geometry_version="geometry-test",
                physics_list="physics-test",
                digitizer_version="digitizer-test",
                trigger_definition="valid_hit(ch1) AND valid_hit(ch2)",
            ),
            {
                "source_mode": "far_field_parallel_beam",
                "generation_area_cm2": 120.0,
                "generated_count_included_zero_deposit_events": True,
            },
        )

    def test_campaign_builds_distinct_sensitivity_and_topology(self):
        library = self._library()
        self.assertTrue(np.allclose(library.sensitivities.conditional.values, 0.1))
        self.assertTrue(np.allclose(library.sensitivities.effective_area.values, 12.0))
        self.assertIsNone(library.sensitivities.finite_distance_emitted)
        self.assertTrue(np.allclose(
            library.calibration_arrays["topology_probability__normal_forward"], 0.8
        ))

    def test_portable_store_roundtrip_and_checksum(self):
        store = PortableNpzJsonResponseStore()
        with tempfile.TemporaryDirectory() as directory:
            store.save(self._library(), directory)
            self.assertTrue(store.is_complete(directory))
            loaded = store.load(directory)
            self.assertEqual(loaded.metadata.library_status, "candidate_unvalidated")
            array = Path(directory) / store.ARRAY_NAME
            with array.open("ab") as stream:
                stream.write(b"corrupt")
            self.assertFalse(store.is_complete(directory))

    def test_hybrid_response_uses_library_sensitivity(self):
        grid = EnergyGrid.nonuniform([0.3, 0.5, 0.8])
        directions = np.asarray([[0.0, 0.0, -1.0], [1.0, 0.0, 0.0]])
        model = HybridMonteCarloResponse(
            arm_sigma_deg=np.full((2, 2), 15.0),
            sensitivity_values=np.full((2, 2), 0.2),
            minimum_relative_weight=1e-8,
        )
        event = MeasuredEvent(
            event_id="hybrid",
            hits=(
                DigitizedHit("h2", Channel.CH2, 0, "1", np.asarray([0.0, 0.0, -30.0]), 0.1),
                DigitizedHit("h1", Channel.CH1, 1, "1", np.asarray([0.0, 0.0, 0.0]), 0.2),
            ),
        )
        response = model.evaluate(event, directions, grid)
        self.assertGreater(response.nonzero_count, 0)
        self.assertTrue(np.all(np.isfinite(response.values)))

    def test_formal_denominator_must_include_zero_deposit_primaries(self):
        library = self._library()
        sky_count, energy_count = library.sensitivities.conditional.shape
        sky, energy = np.indices((sky_count, energy_count))
        table = ResponseNodeTable(
            sky.reshape(-1), energy.reshape(-1),
            np.full(sky_count * energy_count, 100.0),
            np.full(sky_count * energy_count, 10.0),
            np.full(sky_count * energy_count, 5.0),
            {},
        )
        with self.assertRaises(ValueError):
            ResponseCampaignBuilder().build(
                table, library.energy_grid, library.sky_grid, library.metadata,
                {"source_mode": "far_field_parallel_beam", "generation_area_cm2": 10.0},
            )


if __name__ == "__main__":
    unittest.main()
