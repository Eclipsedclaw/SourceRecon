import unittest

import numpy as np

from eiid.detector import ChannelMapping, DigitizedEventBuilder, TruthDigitizer
from eiid.domain import Channel
from eiid.io import LegacyGeant4RootEventSource, LegacyStep, LegacyStepAggregator


class Geant4LegacyTests(unittest.TestCase):
    @staticmethod
    def _source():
        mapping = ChannelMapping(
            {0: "ch2", 1: "ch1", 2: "ch0"},
            {"ch2": 0, "ch1": 1, "ch0": 2},
        )
        return LegacyGeant4RootEventSource(
            root_path="missing.root",
            tree_name="Tree1",
            branches={
                "event_id": "eventID",
                "chamber_id": "chamberID",
                "pixel_id": "pixelID",
                "energy_mev": "eDep_MeV",
                "x_mm": "x_post",
                "y_mm": "y_post",
                "z_mm": "z_post",
                "step_id": "stepID",
                "time_ns": "time_ns",
            },
            mapping=mapping,
            digitizer=TruthDigitizer(),
            dataset_id="d",
        )

    def test_step_aggregation_conserves_energy_and_weights_position(self):
        aggregator = LegacyStepAggregator("d")
        deposits = aggregator.aggregate(
            (
                LegacyStep("1", 0, "5", 0.1, [0, 0, -30], step_order=1),
                LegacyStep("1", 0, "5", 0.3, [2, 0, -30], step_order=2),
                LegacyStep("1", 1, "7", 0.2, [0, 0, 0], step_order=3),
            )
        )
        self.assertEqual(len(deposits), 2)
        first = deposits[0]
        self.assertAlmostEqual(first.total_edep_mev, 0.4)
        self.assertTrue(np.allclose(first.energy_weighted_position_mm, [1.5, 0, -30]))
        self.assertEqual(first.step_count, 2)

    def test_digitized_builder_preserves_pixels(self):
        mapping = ChannelMapping(
            {0: "ch2", 1: "ch1", 2: "ch0"},
            {"ch2": 0, "ch1": 1, "ch0": 2},
        )
        deposits = LegacyStepAggregator("d").aggregate(
            (
                LegacyStep("1", 0, "5", 0.1, [0, 0, -30]),
                LegacyStep("1", 0, "6", 0.1, [1, 0, -30]),
                LegacyStep("1", 1, "7", 0.2, [0, 0, 0]),
            )
        )
        events = DigitizedEventBuilder(mapping, TruthDigitizer()).build(deposits)
        self.assertEqual(len(events), 1)
        self.assertEqual(len(events[0].hits_in_channel(Channel.CH2)), 2)

    def test_chunk_tail_event_is_carried(self):
        records = (
            LegacyStep("1", 0, "0", 0.1, [0, 0, 0]),
            LegacyStep("2", 0, "0", 0.1, [0, 0, 0]),
            LegacyStep("2", 1, "0", 0.1, [0, 0, 1]),
        )
        complete, carry = LegacyGeant4RootEventSource._split_complete_records(records)
        self.assertEqual([item.raw_event_id for item in complete], ["1"])
        self.assertEqual([item.raw_event_id for item in carry], ["2", "2"])

    def test_configured_branch_arrays_become_positive_steps(self):
        source = self._source()
        records = source._records_from_arrays(
            {
                "eventID": np.array([1, 1, 2]),
                "chamberID": np.array([0, 0, 1]),
                "pixelID": np.array([5, 5, 7]),
                "eDep_MeV": np.array([0.1, 0.0, 0.2]),
                "x_post": np.array([0.0, 0.0, 1.0]),
                "y_post": np.array([0.0, 0.0, 0.0]),
                "z_post": np.array([-30.0, -30.0, 0.0]),
                "stepID": np.array([1, 2, 1]),
                "time_ns": np.array([10.0, 10.1, 20.0]),
            }
        )
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].raw_event_id, "1")
        self.assertEqual(records[1].chamber_id, 1)


if __name__ == "__main__":
    unittest.main()
