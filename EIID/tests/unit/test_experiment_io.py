from pathlib import Path
import unittest

from eiid.configuration import load_config
from eiid.detector import TriggerPolicy
from eiid.io import (
    EventIngestionPipeline,
    EventSourceFactory,
    LinearCalibrationTable,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG = PROJECT_ROOT / "config" / "examples" / "experiment_delimited_smoke.json"


class ExperimentIoTests(unittest.TestCase):
    def test_direct_energy_input_and_trigger_pipeline(self):
        config = load_config(str(CONFIG))
        source = EventSourceFactory(config).create()
        policy = TriggerPolicy(
            config.trigger.minimum_hit_energy_mev,
            config.trigger.coincidence_window_ns,
        )
        result = EventIngestionPipeline(source, policy).run()
        self.assertEqual(len(result.dataset.events), 3)
        self.assertEqual(len(result.accepted_events), 2)
        self.assertEqual(len(result.rejected_events), 1)
        event_three = next(
            event for event in result.dataset.events if event.event_id.endswith(":3")
        )
        self.assertEqual(len(event_three.hits), 3)
        self.assertIsNone(event_three.truth)

    def test_linear_calibration_converts_kev_to_mev(self):
        table = LinearCalibrationTable.from_file(
            PROJECT_ROOT / "tests" / "fixtures" / "experiment" / "calibration.tsv",
            delimiter="\t",
            columns={
                "pixel_id": "PixelID",
                "slope_kev_per_adc": "Slope_keV_per_ADC",
                "intercept_kev": "Intercept_keV",
            },
        )
        self.assertAlmostEqual(table.energy_mev("0", 100.0), 0.210)


if __name__ == "__main__":
    unittest.main()

