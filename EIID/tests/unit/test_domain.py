import unittest

import numpy as np

from eiid.domain import (
    Channel,
    DatasetMetadata,
    DigitizedHit,
    EventDataset,
    MeasuredEvent,
    SequenceClass,
    SimulationTruth,
)


def make_hit(hit_id, channel, layer, x):
    return DigitizedHit(
        hit_id=hit_id,
        channel=channel,
        layer=layer,
        pixel_id=hit_id,
        position_mm=[x, 0.0, float(layer)],
        energy_mev=0.1,
    )


class DomainTests(unittest.TestCase):
    def test_same_layer_pixel_hits_are_not_collapsed(self):
        event = MeasuredEvent(
            event_id="e1",
            hits=(
                make_hit("a", Channel.CH2, 0, 0.0),
                make_hit("b", Channel.CH2, 0, 1.0),
                make_hit("c", Channel.CH1, 1, 0.0),
            ),
        )
        self.assertEqual(len(event.hits), 3)
        self.assertEqual(len(event.hits_in_channel(Channel.CH2)), 2)

    def test_backscatter_label_is_retained(self):
        event = MeasuredEvent(
            event_id="back",
            hits=(),
            sequence_class=SequenceClass.BACKSCATTER,
        )
        self.assertEqual(event.sequence_class, SequenceClass.BACKSCATTER)

    def test_observable_copy_removes_simulation_truth(self):
        truth = SimulationTruth(
            primary_energy_mev=0.662,
            propagation_direction_detector=[0.0, 0.0, 1.0],
            source_direction_detector=[0.0, 0.0, -1.0],
        )
        event = MeasuredEvent(event_id="sim", hits=(), truth=truth)
        dataset = EventDataset(
            events=(event,),
            metadata=DatasetMetadata("d", "geant4", "0.1.0"),
        )
        observable = dataset.observable_copy()
        self.assertIsNone(observable.events[0].truth)
        self.assertIsNotNone(dataset.events[0].truth)


if __name__ == "__main__":
    unittest.main()

