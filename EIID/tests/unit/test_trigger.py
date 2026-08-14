import unittest

from eiid.detector import TriggerPolicy
from eiid.domain import Channel, DigitizedHit, MeasuredEvent, RejectionReason


def hit(hit_id, channel, layer, energy=0.1, time_ns=1.0, valid=True):
    return DigitizedHit(
        hit_id=hit_id,
        channel=channel,
        layer=layer,
        pixel_id="0",
        position_mm=[0.0, 0.0, float(layer)],
        energy_mev=energy,
        time_ns=time_ns,
        is_valid_readout=valid,
    )


class TriggerTests(unittest.TestCase):
    def setUp(self):
        self.policy = TriggerPolicy({"ch0": 0.01, "ch1": 0.01, "ch2": 0.01})

    def test_ch1_and_ch2_trigger_without_ch0(self):
        event = MeasuredEvent(
            event_id="two",
            hits=(hit("a", Channel.CH2, 0), hit("b", Channel.CH1, 1)),
        )
        self.assertTrue(self.policy.evaluate(event).accepted)

    def test_ch0_does_not_rescue_missing_ch2(self):
        event = MeasuredEvent(
            event_id="no_ch2",
            hits=(hit("a", Channel.CH1, 1), hit("b", Channel.CH0, 2)),
        )
        decision = self.policy.evaluate(event)
        self.assertFalse(decision.accepted)
        self.assertTrue(decision.reasons & RejectionReason.MISSING_CH2)

    def test_threshold_is_applied_after_digitization(self):
        event = MeasuredEvent(
            event_id="threshold",
            hits=(
                hit("a", Channel.CH2, 0, energy=0.005),
                hit("b", Channel.CH1, 1),
            ),
        )
        self.assertFalse(self.policy.evaluate(event).accepted)

    def test_configured_coincidence_window_is_enforced(self):
        policy = TriggerPolicy(
            {"ch0": 0.0, "ch1": 0.0, "ch2": 0.0},
            coincidence_window_ns=2.0,
        )
        event = MeasuredEvent(
            event_id="late",
            hits=(
                hit("a", Channel.CH2, 0, time_ns=0.0),
                hit("b", Channel.CH1, 1, time_ns=5.0),
            ),
        )
        decision = policy.evaluate(event)
        self.assertFalse(decision.accepted)
        self.assertTrue(decision.reasons & RejectionReason.COINCIDENCE_FAILED)


if __name__ == "__main__":
    unittest.main()

