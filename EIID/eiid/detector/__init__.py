"""探测器映射、数字化与触发规则。"""

from .channel_map import ChannelMapping
from .digitizer import DigitizedEventBuilder, Digitizer, TruthDigitizer
from .trigger import TriggerDecision, TriggerPolicy

__all__ = [
    "ChannelMapping",
    "DigitizedEventBuilder",
    "Digitizer",
    "TriggerDecision",
    "TriggerPolicy",
    "TruthDigitizer",
]

